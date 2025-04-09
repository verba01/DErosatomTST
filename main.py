import asyncio
from app.services.flightradar_services import FlightDataService


async def main():
    service = FlightDataService()

    print("\n🛫 Сервис мониторинга рейсов запущен")
    print("⏳ Первоначальный сбор данных...")

    try:
        # Первоначальный сбор данных
        result = await service.save_flight_data()
        if result:
            print(f"✅ Данные успешно сохранены")
            if hasattr(result, 'map_path'):
                print(f"✔ Карта: {result.map_path}")
            elif isinstance(result, dict) and 'map' in result:
                print(f"✔ Карта: {result['map']}")

        # Запуск периодического сбора
        task = asyncio.create_task(service.run_periodically())

        while True:
            command = input("\nВведите команду (hour/day/map/exit): ").strip().lower()

            if command == "hour":
                flights = await service.get_last_hour_flights()
                print(f"\nРейсы за последний час ({len(flights)}):")
                for i, flight in enumerate(flights[:20], 1):
                    print(
                        f"{i}. {flight.callsign} | "
                        f"{flight.aircraft_code if hasattr(flight, 'aircraft_code') else 'N/A'} | "
                        f"{flight.origin_airport or '?'}→{flight.destination_airport or '?'}"
                    )

            elif command == "day":
                stats = await service.get_last_day_stats()
                print("\n📊 Статистика за 24 часа:")
                for i, (model, count) in enumerate(stats[:10], 1):
                    print(f"{i}. {model}: {count} рейсов")

            elif command == "map":
                print("\n🔄 Генерация новой карты...")
                result = await service.save_flight_data()
                if result and hasattr(result, 'map_path'):
                    print(f"✔ Карта сохранена: {result.map_path}")
                elif result and isinstance(result, dict):
                    print(f"✔ Карта сохранена: {result.get('map', 'неизвестно')}")
                else:
                    print("❌ Не удалось сгенерировать карту")

            elif command == "exit":
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                print("\n🛑 Сервис остановлен")
                break

            else:
                print("\n⚠️ Доступные команды: hour, day, map, exit")

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {str(e)}")
        if 'task' in locals():
            task.cancel()
            await task


if __name__ == "__main__":
    asyncio.run(main())