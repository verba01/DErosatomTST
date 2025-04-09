from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base_class import Base


class Flight(Base):
    __tablename__ = "flights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    callsign = Column(String(20), index=True, nullable=False)
    icao24 = Column(String(20), index=True)
    aircraft_code = Column(String(10))
    airline = Column(String(100))
    airline_code = Column(String(10))  # Добавлено новое поле (IATA код)
    airline_icao = Column(String(10))  # Добавлено новое поле (ICAO код)
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Integer)
    speed = Column(Integer)
    origin_airport = Column(String(10))
    destination_airport = Column(String(10))
    timestamp = Column(DateTime, index=True)


class FlightStats(Base):
    __tablename__ = "flight_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period = Column(String(20), nullable=False)  # 'hourly' или 'daily'
    start_time = Column(DateTime, nullable=False)
    aircraft_model = Column(String(50))
    airline = Column(String(100))
    flight_count = Column(Integer, nullable=False)