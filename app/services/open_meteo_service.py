import httpx
from fastapi import HTTPException
from typing import Dict, Any, List, Optional

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: {"description": "Ясно", "icon_day": "sun.svg", "icon_night": "moon.svg"},
    1: {"description": "В основном ясно", "icon_day": "cloud-sun.svg", "icon_night": "cloud-moon.svg"},
    2: {"description": "Переменная облачность", "icon_day": "cloud.svg", "icon_night": "cloud.svg"},
    3: {"description": "Пасмурно", "icon_day": "clouds.svg", "icon_night": "clouds.svg"}, # Используем множественное число для "пасмурно"
    45: {"description": "Туман", "icon_day": "align-justify.svg", "icon_night": "align-justify.svg"}, # Feather icon для тумана (placeholder)
    48: {"description": "Изморозь (иней)", "icon_day": "snowflake.svg", "icon_night": "snowflake.svg"}, # Placeholder
    51: {"description": "Морось: легкая", "icon_day": "cloud-drizzle.svg", "icon_night": "cloud-drizzle.svg"},
    53: {"description": "Морось: умеренная", "icon_day": "cloud-drizzle.svg", "icon_night": "cloud-drizzle.svg"},
    55: {"description": "Морось: плотная", "icon_day": "cloud-drizzle.svg", "icon_night": "cloud-drizzle.svg"},
    56: {"description": "Ледяная морось: легкая", "icon_day": "cloud-drizzle.svg", "icon_night": "cloud-drizzle.svg"}, # Placeholder
    57: {"description": "Ледяная морось: плотная", "icon_day": "cloud-drizzle.svg", "icon_night": "cloud-drizzle.svg"}, # Placeholder
    61: {"description": "Дождь: небольшой", "icon_day": "cloud-rain.svg", "icon_night": "cloud-rain.svg"},
    63: {"description": "Дождь: умеренный", "icon_day": "cloud-rain.svg", "icon_night": "cloud-rain.svg"},
    65: {"description": "Дождь: сильный", "icon_day": "cloud-lightning-rain.svg", "icon_night": "cloud-lightning-rain.svg"}, # Дождь с грозой для сильного дождя
    66: {"description": "Ледяной дождь: легкий", "icon_day": "cloud-rain.svg", "icon_night": "cloud-rain.svg"}, # Placeholder
    67: {"description": "Ледяной дождь: сильный", "icon_day": "cloud-lightning-rain.svg", "icon_night": "cloud-lightning-rain.svg"}, # Placeholder
    71: {"description": "Снег: небольшой", "icon_day": "cloud-snow.svg", "icon_night": "cloud-snow.svg"},
    73: {"description": "Снег: умеренный", "icon_day": "cloud-snow.svg", "icon_night": "cloud-snow.svg"},
    75: {"description": "Снег: сильный", "icon_day": "cloud-snow.svg", "icon_night": "cloud-snow.svg"},
    77: {"description": "Снежные зерна", "icon_day": "cloud-snow.svg", "icon_night": "cloud-snow.svg"}, # Placeholder
    80: {"description": "Ливни: небольшие", "icon_day": "cloud-rain.svg", "icon_night": "cloud-rain.svg"},
    81: {"description": "Ливни: умеренные", "icon_day": "cloud-rain.svg", "icon_night": "cloud-rain.svg"},
    82: {"description": "Ливни: сильные", "icon_day": "cloud-lightning-rain.svg", "icon_night": "cloud-lightning-rain.svg"},
    85: {"description": "Снегопады: небольшие", "icon_day": "cloud-snow.svg", "icon_night": "cloud-snow.svg"},
    86: {"description": "Снегопады: сильные", "icon_day": "cloud-snow.svg", "icon_night": "cloud-snow.svg"},
    95: {"description": "Гроза: небольшая или умеренная", "icon_day": "cloud-lightning.svg", "icon_night": "cloud-lightning.svg"},
    96: {"description": "Гроза с небольшим градом", "icon_day": "cloud-lightning-rain.svg", "icon_night": "cloud-lightning-rain.svg"}, # Placeholder
    99: {"description": "Гроза с сильным градом", "icon_day": "cloud-lightning-rain.svg", "icon_night": "cloud-lightning-rain.svg"}, # Placeholder
}

async def get_city_coordinates(city_name: str) -> Optional[Dict[str, Any]]:
    # получае координаты для указанного города и возвращает первых рез из ответа или None, если не найденр
    params = {"name": city_name, "count": 1, "language": "ru", "format": "json"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(GEOCODING_API_URL, params=params)
            response.raise_for_status() # для ошибок 4xx/5xx
            data = response.json()
            
            if "results" in data and len(data["results"]) > 0:
                # первый подходящий рез выдаем
                city_info = data["results"][0]
                return {
                    "name": city_info.get("name", city_name), # имя от апи используем или введенное
                    "admin1": city_info.get("admin1"), # Область/регион
                    "country": city_info.get("country"),
                    "latitude": city_info["latitude"],
                    "longitude": city_info["longitude"]
                }
            return None
        except httpx.HTTPStatusError as e:
            print(f"Возникла ошибка HTTP при геокодировании города {city_name}: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"При геокодировании города произошла непредвиденная ошибка {city_name}: {e}")
            return None

async def get_weather_forecast(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    # получаем прогноз для указанных координат
    params = {
         "latitude": latitude,
        "longitude": longitude,
        "current_weather": "true",
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum,windspeed_10m_max", # Данные на день
        "timezone": "auto",  # автоматическое определение временной зоны
        "forecast_days": 7    # прогноз на 7 дней
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(WEATHER_API_URL, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"При получении информации о погоде произошла HTTP ошибка: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"При получении информации о погоде произошла непредвиденная ошибка: {e}")
            return None
 
# ищет города для автодопа по фрагменту из названия, включая координаты, и возвращается список словарей о городах с инфо          
async def search_cities_for_autocomplete(query_fragment: str, count: int = 5) -> List[Dict[str, Any]]:
    params = {"name": query_fragment, "count": count, "language": "ru", "format": "json"}
    cities_found = []
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(GEOCODING_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "results" in data and len(data["results"]) > 0:
                for city_info in data["results"]:
                    cities_found.append({
                        "name": city_info.get("name", query_fragment),
                        "admin1": city_info.get("admin1"),
                        "country": city_info.get("country"),
                        "latitude": city_info.get("latitude"),
                        "longitude": city_info.get("longitude")
                    })
            return cities_found
        except httpx.HTTPStatusError as e:
            print(f"При автодополнении поиска произошла HTTP ошибка для '{query_fragment}': {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            print(f"При автодополнении поиска произошла непредвиденная ошибка для '{query_fragment}': {e}")
    return cities_found