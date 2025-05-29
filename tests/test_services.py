import pytest
import httpx
from respx import MockRouter

from app.services import open_meteo_service

# все тесты асинхрон
pytestmark = pytest.mark.asyncio

# функция находит город
async def test_get_city_coordinates_success(respx_mock: MockRouter):
    city_name = "Berlin"
    # ожидаемые параметры для URL, который будет запрашивать наш сервис
    expected_params = {"name": city_name, "count": 1, "language": "ru", "format": "json"}
    mock_api_response_data = {
        "results": [
            {
                "id": 1, "name": "Berlin", "latitude": 52.52, "longitude": 13.40,
                "country_code": "DE", "timezone": "Europe/Berlin", "country": "Germany", "admin1": "Berlin"
            }
        ]
    }
    
    respx_mock.get(open_meteo_service.GEOCODING_API_URL, params=expected_params).respond(status_code=200, json=mock_api_response_data)
    
    # respx ответ перехватит и вернет наш мокнутый
    result = await open_meteo_service.get_city_coordinates(city_name)

    assert result is not None
    assert result["name"] == "Berlin"
    assert result["country"] == "Germany"
    assert result["latitude"] == 52.52

    # проверяем что мокнутый URL был вызван:
    assert respx_mock.calls.call_count == 1
    called_request = respx_mock.calls.last.request
    assert called_request.method == "GET"
    assert str(called_request.url.host) == "geocoding-api.open-meteo.com"
    assert str(called_request.url.path) == "/v1/search"

# город не найден и возвращается пустой список резов
async def test_get_city_coordinates_not_found(respx_mock: MockRouter):
    city_name = "НеСуществует228"
    expected_params = {"name": city_name, "count": 1, "language": "ru", "format": "json"}
    
    # апи от open-meteo если не нашло, то 200 и пусто список
    mock_api_response_data = {"results": []}
    respx_mock.get(open_meteo_service.GEOCODING_API_URL, params=expected_params).respond(status_code=200, json=mock_api_response_data)
    
    result = await open_meteo_service.get_city_coordinates(city_name)
    
    assert result is None # если город не найден, то нан
    assert respx_mock.calls.call_count == 1
    
# внешний сервис допустим не отвечает или любая другая ошибка
async def test_get_city_coordinates_api_http_error(respx_mock: MockRouter):
    city_name = "ErrorCity"
    expected_params = {"name": city_name, "count": 1, "language": "ru", "format": "json"}
    respx_mock.get(open_meteo_service.GEOCODING_API_URL, params=expected_params).respond(status_code=500, json={"reason": "Internal Server Error"})
    
    result = await open_meteo_service.get_city_coordinates(city_name)
    
    assert result is None # наша функция возвращает нан через response.raise_for_status()
    assert respx_mock.calls.call_count == 1
    
# ошибка сеи к api (ConnectionError)
async def test_get_city_coordinates_network_error(respx_mock: MockRouter):
    city_name = "NetworkFailCity"
    expected_params = {"name": city_name, "count": 1, "language": "ru", "format": "json"}
    respx_mock.get(open_meteo_service.GEOCODING_API_URL, params=expected_params).mock(side_effect=httpx.ConnectError("Failed to connect"))
    
    result = await open_meteo_service.get_city_coordinates(city_name)
    
    assert result is None # except Exception ловит данные ошибки 
    assert respx_mock.calls.call_count == 1
    
# !!! тесты для автодопа !!!
# успешное автодополнение городов
async def test_search_cities_for_autocomplete_success(respx_mock: MockRouter):
    query_fragment = "Бер"
    expected_count = 3 # запрос трех городов для автодопа
    expected_params = {"name": query_fragment, "count": expected_count, "language": "ru", "format": "json"}
    mock_api_response_data = {
        "results": [
            {"name": "Берлин", "admin1": "Берлин", "country": "Германия", "latitude": 52.52, "longitude": 13.40},
            {"name": "Берн", "admin1": "Берн", "country": "Швейцария", "latitude": 46.94, "longitude": 7.44},
            {"name": "Берген", "admin1": "Вестланн", "country": "Норвегия", "latitude": 60.39, "longitude": 5.32}
        ]
    }
    respx_mock.get(open_meteo_service.GEOCODING_API_URL, params=expected_params).respond(status_code=200, json=mock_api_response_data)
    
    result = await open_meteo_service.search_cities_for_autocomplete(query_fragment, count=expected_count)
    
    assert result is not None
    assert len(result) == 3
    assert result[0]["name"] == "Берлин"
    assert result[1]["country"] == "Швейцария"
    assert "latitude" in result[2] 
    assert respx_mock.calls.call_count == 1
    
# !!! тесты для get_weather_forecast (аналогично)
# успешное получение погоды
async def test_get_weather_forecast_success(respx_mock: MockRouter):
    lat, lon = 52.52, 13.40 # Берлин
    expected_params = { # параметры посылаемые на open-meteo
        "latitude": lat, "longitude": lon, "current_weather": "true",
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum,windspeed_10m_max",
        "timezone": "auto", "forecast_days": 7
    }
    mock_forecast_api_response = {
        "latitude": lat, "longitude": lon, "timezone": "Europe/Berlin",
        "current_weather": {"temperature": 15.0, "weathercode": 3, "windspeed": 10.0, "is_day": 1},
        "daily": {} # какие то данные внутри, для теста пусто будет
    }
    respx_mock.get(open_meteo_service.WEATHER_API_URL, params=expected_params).respond(status_code=200, json=mock_forecast_api_response)
    
    result = await open_meteo_service.get_weather_forecast(lat, lon)
    
    assert result is not None
    assert result["latitude"] == lat
    assert "current_weather" in result
    assert result["current_weather"]["temperature"] == 15.0
    assert respx_mock.calls.call_count == 1