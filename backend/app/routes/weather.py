from fastapi import APIRouter

from app.services.weather_service import WeatherService

router = APIRouter()

@router.get("/weather")
def get_weather(
    lat: float,
    lon: float
):
    return WeatherService.get_weather(lat, lon)