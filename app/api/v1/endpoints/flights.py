from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.flightradar_services_1 import get_flights_report
from sqlalchemy import func
from sqlalchemy.future import select

from db.models import Airline, Flight

router = APIRouter()


@router.get("/reports/aircraft")
async def aircraft_report(db: AsyncSession = Depends(get_db)):
    return await get_flights_report()


@router.get("/reports/airlines")
async def airlines_report(db: AsyncSession = Depends(get_db)):
    async with db as session:
        stmt = select(
            Airline.name,
            Airline.icao_code,
            func.count(Flight.id).label("flights_count")
        ).join(
            Flight.airline
        ).group_by(
            Airline.name,
            Airline.icao_code
        )

        result = await session.execute(stmt)
        return result.all()