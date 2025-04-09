import asyncio
import csv
import folium
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from FlightRadar24 import FlightRadar24API
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import async_session

DATA_DIR = Path("app/data")
DATA_DIR.mkdir(exist_ok=True)
fr_api = FlightRadar24API()


@dataclass
class SaveResult:
    db: str
    csv_path: str
    map_path: str


class FlightDataService:
    def __init__(self):
        self.airport_cache: Dict[str, dict] = {}
        self.airline_cache: Dict[str, dict] = {}  # {ICAO: {'name': str, 'code': str}}
        self.black_sea_coords = (43.0, 34.0)
        self.is_running = True

    async def _init_airline_cache(self):
        """Инициализирует кэш авиакомпаний из API"""
        try:
            airlines = fr_api.get_airlines()
            for airline in airlines:
                icao = airline.get('ICAO', '').upper()
                if icao:  # Используем только записи с валидным ICAO кодом
                    self.airline_cache[icao] = {
                        'name': airline.get('Name', icao),
                        'code': airline.get('Code', ''),
                        'icao': icao
                    }
            print(f"Загружено {len(self.airline_cache)} авиакомпаний в кэш")
        except Exception as e:
            print(f"Ошибка при загрузке списка авиакомпаний: {e}")

    def _get_airline_info(self, flight_obj) -> dict:
        """Возвращает полную информацию об авиакомпании для рейса"""
        # 1. Пробуем получить данные из атрибутов flight
        airline_icao = getattr(flight_obj, 'airline_icao', '').upper()
        airline_name = getattr(flight_obj, 'airline', '')
        airline_code = getattr(flight_obj, 'airline_iata', '')

        # 2. Если нет ICAO, пробуем извлечь из callsign (первые 3 символа)
        if not airline_icao and hasattr(flight_obj, 'callsign'):
            airline_icao = flight_obj.callsign[:3].upper()

        # 3. Ищем в кэше
        if airline_icao in self.airline_cache:
            return self.airline_cache[airline_icao]

        # 4. Если не нашли, возвращаем то, что есть
        return {
            'name': airline_name if airline_name else airline_icao,
            'code': airline_code,
            'icao': airline_icao
        }

    async def get_airport_details(self, code: str) -> Optional[dict]:
        """Получает детали аэропорта с кэшированием"""
        if not code:
            return None

        if code not in self.airport_cache:
            try:
                details = fr_api.get_airport(code=code)
                self.airport_cache[code] = {
                    'name': getattr(details, 'name', f'Airport {code}'),
                    'icao': getattr(details, 'icao', code),
                    'iata': getattr(details, 'iata', code),
                    'country': getattr(details, 'country', 'Unknown')
                }
            except Exception as e:
                print(f"Ошибка получения данных аэропорта {code}: {e}")
                self.airport_cache[code] = {
                    'name': f'Airport {code}',
                    'icao': code,
                    'iata': code,
                    'country': 'Unknown'
                }
        return self.airport_cache[code]

    def _generate_flight_map(self, flights) -> Path:
        """Генерирует интерактивную карту рейсов"""
        m = folium.Map(location=self.black_sea_coords, zoom_start=7)

        for flight in flights:
            if hasattr(flight, 'latitude') and hasattr(flight, 'longitude'):
                origin = getattr(flight, 'origin_airport_iata', '?')
                dest = getattr(flight, 'destination_airport_iata', '?')
                airline_info = self._get_airline_info(flight)

                folium.Marker(
                    [flight.latitude, flight.longitude],
                    popup=(
                        f"✈ {flight.callsign}<br>"
                        f"Модель: {getattr(flight, 'aircraft_code', 'N/A')}<br>"
                        f"Авиакомпания: {airline_info['name']}<br>"
                        f"Код: {airline_info['code']}<br>"
                        f"Высота: {flight.altitude} ft<br>"
                        f"Скорость: {flight.ground_speed} узлов<br>"
                        f"Маршрут: {origin} → {dest}"
                    ),
                    icon=folium.Icon(color="red", icon="plane")
                ).add_to(m)

        map_path = DATA_DIR / "black_sea_flights.html"
        m.save(map_path)
        return map_path

    async def _save_to_db(self, session: AsyncSession, flights):
        """Сохраняет рейсы в базу данных"""
        from app.db.models.flight import Flight

        for flight in flights:
            airline_info = self._get_airline_info(flight)
            db_flight = Flight(
                callsign=flight.callsign,
                icao24=getattr(flight, 'icao_24bit', None),
                aircraft_code=getattr(flight, 'aircraft_code', 'UNKNOWN'),
                airline=airline_info['name'],
                airline_code=airline_info['code'],
                airline_icao=airline_info['icao'],
                latitude=flight.latitude,
                longitude=flight.longitude,
                altitude=flight.altitude,
                speed=flight.ground_speed,
                origin_airport=getattr(flight, 'origin_airport_iata', None),
                destination_airport=getattr(flight, 'destination_airport_iata', None),
                timestamp=datetime.now()
            )
            session.add(db_flight)
        await session.commit()

    async def save_flight_data(self) -> Optional[SaveResult]:
        """Основной метод сбора и сохранения данных"""
        try:
            if not hasattr(self, 'airline_cache_loaded'):
                await self._init_airline_cache()
                self.airline_cache_loaded = True

            bounds = fr_api.get_bounds_by_point(*self.black_sea_coords, 300000)
            flights = fr_api.get_flights(bounds=bounds)

            if not flights:
                print("⚠️ Нет данных о рейсах в указанной зоне!")
                return None

            timestamp = datetime.now()
            csv_path = DATA_DIR / f"flights_{timestamp.strftime('%Y%m%d')}.csv"
            file_exists = csv_path.exists()

            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'timestamp',
                    'callsign',
                    'aircraft_code',
                    'airline_name',
                    'airline_code',
                    'airline_icao',
                    'altitude_ft',
                    'speed_knots',
                    'origin_icao',
                    'origin_name',
                    'origin_country',
                    'destination_icao',
                    'destination_name',
                    'destination_country',
                    'route_description'
                ])

                if not file_exists:
                    writer.writeheader()

                for i, flight in enumerate(flights, 1):
                    try:
                        # Получаем полную информацию об авиакомпании
                        airline_info = self._get_airline_info(flight)

                        # Получаем данные аэропортов
                        origin_iata = getattr(flight, 'origin_airport_iata', None)
                        dest_iata = getattr(flight, 'destination_airport_iata', None)
                        origin_details = await self.get_airport_details(origin_iata) if origin_iata else None
                        dest_details = await self.get_airport_details(dest_iata) if dest_iata else None

                        # Формируем запись для CSV
                        row_data = {
                            'timestamp': timestamp.isoformat(),
                            'callsign': flight.callsign,
                            'aircraft_code': getattr(flight, 'aircraft_code', 'N/A'),
                            'airline_name': airline_info['name'],
                            'airline_code': airline_info['code'],
                            'airline_icao': airline_info['icao'],
                            'altitude_ft': flight.altitude,
                            'speed_knots': flight.ground_speed,
                            'origin_icao': origin_details['icao'] if origin_details else '',
                            'origin_name': origin_details['name'] if origin_details else '',
                            'origin_country': origin_details['country'] if origin_details else '',
                            'destination_icao': dest_details['icao'] if dest_details else '',
                            'destination_name': dest_details['name'] if dest_details else '',
                            'destination_country': dest_details['country'] if dest_details else '',
                            'route_description': (
                                f"{origin_details['icao'] if origin_details else '?'} "
                                f"({origin_details['name'] if origin_details else 'Unknown'}) → "
                                f"{dest_details['icao'] if dest_details else '?'} "
                                f"({dest_details['name'] if dest_details else 'Unknown'})"
                            )
                        }

                        writer.writerow(row_data)

                        if i % 50 == 0:
                            print(f"Обработано {i}/{len(flights)} рейсов")

                    except Exception as e:
                        print(f"Ошибка обработки рейса {getattr(flight, 'callsign', 'UNKNOWN')}: {e}")

            # Сохранение в базу данных
            async with async_session() as session:
                await self._save_to_db(session, flights)

            # Генерация карты
            map_path = self._generate_flight_map(flights)

            return SaveResult(
                db="PostgreSQL",
                csv_path=str(csv_path),
                map_path=str(map_path)
            )

        except Exception as e:
            print(f"❌ Критическая ошибка при сохранении данных: {e}")
            return None

    async def run_periodically(self, interval_minutes=59):
        """Запускает периодический сбор данных"""
        while self.is_running:
            try:
                result = await self.save_flight_data()
                if result:
                    print(f"🔄 Данные сохранены. Карта: {result.map_path}")
            except Exception as e:
                print(f"❌ Ошибка при периодическом сборе: {e}")

            await asyncio.sleep(interval_minutes * 60)

    async def get_last_hour_flights(self) -> List:
        """Возвращает рейсы за последний час из базы данных"""
        from app.db.models.flight import Flight
        from app.db.session import async_session

        async with async_session() as session:
            hour_ago = datetime.now() - timedelta(hours=1)
            result = await session.execute(
                select(Flight).where(Flight.timestamp >= hour_ago)
            )
            return result.scalars().all()

    async def get_last_day_stats(self) -> List[Tuple[str, int]]:
        """Возвращает статистику за последние 24 часа из базы данных"""
        from app.db.models.flight import Flight
        from app.db.session import async_session
        from sqlalchemy import func

        async with async_session() as session:
            day_ago = datetime.now() - timedelta(days=1)
            result = await session.execute(
                select(
                    Flight.aircraft_code,
                    func.count(Flight.id).label('count')
                ).where(
                    Flight.timestamp >= day_ago
                ).group_by(
                    Flight.aircraft_code
                ).order_by(
                    func.count(Flight.id).desc()
                )
            )
            return result.all()