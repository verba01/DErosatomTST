from FlightRadar24 import FlightRadar24API
import folium
from datetime import datetime

fr_api = FlightRadar24API()

latitude = 43.0
longitude = 34.0
radius = 300000

bounds = fr_api.get_bounds_by_point(latitude, longitude, radius)

flights = fr_api.get_flights(bounds=bounds)

airline_icao = "THY"
aircraft_type = "B738"

filtered_flights = fr_api.get_flights(
    bounds=bounds,
    airline=airline_icao,
    aircraft_type=aircraft_type
)

print(f"\n🛫 Рейсы над Чёрным морем ({datetime.now().strftime('%Y-%m-%d %H:%M')}):")
for flight in flights:
    print(
        f"🔹 {flight.callsign} | "
        f"{flight.aircraft_code} | "
        f"Высота: {flight.altitude} футов | "
        f"Скорость: {flight.ground_speed} узлов | "
        f"Маршрут: {flight.origin_airport_iata or '?'} → {flight.destination_airport_iata or '?'}"
    )

print("\nСоздание карты...")
m = folium.Map(location=[latitude, longitude], zoom_start=7)

for flight in flights:
    if hasattr(flight, 'latitude') and hasattr(flight, 'longitude'):
        folium.Marker(
            [flight.latitude, flight.longitude],
            popup=f"✈ {flight.callsign}<br>"
                 f"{flight.aircraft_code}<br>"
                 f"Alt: {flight.altitude} ft",
            icon=folium.Icon(color="red")
        ).add_to(m)

m.save("black_sea_flights_train.html")
print("✔ Карта сохранена в black_sea_flights_train.html")

print("\n📊 Статистика:")
print(f"Всего рейсов: {len(flights)}")
print(f"Турецких авиалиний (THY): {len([f for f in flights if f.airline_icao == 'THY'])}")
print(f"Boeing 737-800: {len([f for f in flights if f.aircraft_code == 'B738'])}")