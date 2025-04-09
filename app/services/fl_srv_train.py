from FlightRadar24 import FlightRadar24API
from datetime import datetime, timezone
import asyncio
from typing import Optional, Dict

# Инициализация API
fr_api = FlightRadar24API()

# Кэш для данных об аэропортах
airport_cache: Dict[str, dict] = {}


async def get_airport_details(code: str, is_iata: bool = True) -> Optional[dict]:
    """Получает детали аэропорта с кэшированием"""
    if not code:
        return None

    cache_key = f"{code}_{'iata' if is_iata else 'icao'}"

    if cache_key not in airport_cache:
        try:
            details = fr_api.get_airport(code=code, details=True)
            airport_cache[cache_key] = {
                'name': getattr(details, 'name', f'Airport {code}'),
                'icao': getattr(details, 'icao', None),
                'iata': getattr(details, 'iata', None),
                'latitude': getattr(details, 'latitude', None),
                'longitude': getattr(details, 'longitude', None),
                'country': getattr(details, 'country', None)
            }
        except Exception as e:
            print(f"Ошибка получения данных аэропорта {code}: {e}")
            airport_cache[cache_key] = None

    return airport_cache.get(cache_key)


async def process_flights():
    """Основная функция обработки рейсов"""
    bounds = fr_api.get_bounds_by_point(43.0, 34.0, 300000)
    flights = fr_api.get_flights(bounds=bounds)

    enriched_flights = []

    for flight in flights:
        try:
            # Получаем коды аэропортов
            origin_iata = getattr(flight, 'origin_airport_iata', None)
            dest_iata = getattr(flight, 'destination_airport_iata', None)

            # Получаем детали аэропортов
            origin_details = await get_airport_details(origin_iata) if origin_iata else None
            dest_details = await get_airport_details(dest_iata) if dest_iata else None

            # Формируем строку маршрута
            route_str = ""
            if origin_iata and origin_details:
                route_str += f"{origin_details['icao'] or '?'} ({origin_details['name']})"
            else:
                route_str += "?"

            route_str += " → "

            if dest_iata and dest_details:
                route_str += f"{dest_details['icao'] or '?'} ({dest_details['name']})"
            else:
                route_str += "?"

            enriched_flight = {
                'callsign': flight.callsign,
                'aircraft': flight.aircraft_code,
                'airline': getattr(flight, 'airline', 'Unknown'),
                'altitude': flight.altitude,
                'speed': flight.ground_speed,
                'route': route_str,
                'route_icao': f"{origin_details['icao'] if origin_details else '?'} → {dest_details['icao'] if dest_details else '?'}"
            }
            enriched_flights.append(enriched_flight)

        except Exception as e:
            print(f"Ошибка обработки рейса {getattr(flight, 'callsign', 'UNKNOWN')}: {e}")

    return enriched_flights


def print_flights_list(flights: list):
    """Выводит список рейсов в консоль"""
    print("\n✈ Список рейсов:")
    for i, flight in enumerate(flights, 1):
        print(
            f"{i}. {flight['callsign']} | "
            f"{flight['aircraft']} | "
            f"{flight['airline']} | "
            f"Высота: {flight['altitude']} ft | "
            f"Скорость: {flight['speed']} узлов | "
            f"Маршрут: {flight['route']}"
        )


async def main():
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    print(f"\n🛫 Сбор данных о рейсах над Чёрным морем ({current_time})")

    flights = await process_flights()
    print_flights_list(flights)  # Показываем первые 20 рейсов


if __name__ == "__main__":
    asyncio.run(main())