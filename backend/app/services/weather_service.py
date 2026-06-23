import openmeteo_requests

import pandas as pd
import requests_cache
import requests
from retry_requests import retry

cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)
class WeatherService:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    @staticmethod
    def get_weather(lat: float, lon: float):
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m",
                "precipitation_probability",
                "wind_speed_10m"
            ],
            "timezone": "Europe/Bucharest"
}

        #response = requests.get(
        #    WeatherService.BASE_URL,
        #    params = params,
        #    timeout = 10
        #)

        responses = openmeteo.weather_api(WeatherService.BASE_URL, params = params)

        response = responses[0]

        return {
            "latitude": response.Latitude(),
            "longitude": response.Longitude(),
            "timezone": response.Timezone()
}