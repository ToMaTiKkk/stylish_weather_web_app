import pytest
import uuid
from httpx import AsyncClient
from fastapi import status

from app.schemas import history_schema
from app.services import open_meteo_service

# для асинжронный тестовы функций
pytestmark = pytest.mark.asyncio

# главная страница отдает HTML и устанавливает user_id cookie если его нет
async def test_read_root_sets_cookie(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]
    assert "user_id" in response.cookies # проверяем наличие куки
    # проверяем что это UUID
    try:
        uuid.UUID(response.cookies["user_id"])
    except ValueError:
        pytest.fail("user_id cookie не валиден UUID")
        
# главная страница использует существующий куки user_id и не перезаписывает его без причины
async def test_read_root_uses_existing_cookie(client: AsyncClient):
    initial_user_id = "test-user-123"
    cookies = {"user_id": initial_user_id}
    headers = {"Cookie": f"user_id={initial_user_id}"} 
    
    response1 = await client.get("/", headers=headers)
    assert response1.status_code == status.HTTP_200_OK
    # если куки уже есть, то UUID перезаписывать не должен
    assert "user_id" not in response1.cookies
    
    # сделаем на всякий и второй такой же запрос
    response2 = await client.get("/", headers=headers)
    assert response2.status_code == status.HTTP_200_OK
    assert "user_id" not in response2.cookies

# тест успешного получения погоды для существующего города
async def test_get_weather_success(client: AsyncClient, mocker, db_session): # db_session чтобы проверить запись в историю
    city_name = "Москва"
    user_id  = "test-user-weather"
    cookies = {"user_id": user_id}
    
    # ответ от сервиса open-meteo
    mock_coords = {
            "name": "Москва", 
            "admin1": "Москва", 
            "country": "Россия", 
            "latitude": 55.75222, 
            "longitude": 37.61556
    }
    # ответ упрощенный с погодой
    mock_forecast = {"latitude": 55.75222, "longitude": 37.61556, "timezone": "Europe/Moscow", 
            "current_weather": {"temperature": 23.0, "weathercode": 3, "windspeed": 10.0, "is_day": 1},
            "daily": {
                "time": ["2025-05-29"], "temperature_2m_max": [27.0], "temperature_2m_min": [13.0],
                "weathercode": [3], "sunrise": ["2025-05-29T08:00"], "sunset": ["2025-05-29T16:00"],
                "precipitation_sum": [0.5], "windspeed_10m_max": [12.0]
            }
    }
    mocker.patch("app.services.open_meteo_service.get_city_coordinates", return_value=mock_coords)
    mocker.patch("app.services.open_meteo_service.get_weather_forecast", return_value=mock_forecast)
    
    client.cookies = cookies
    response = await client.get(f"/api/weather/{city_name}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["city_info"]["name"] == "Москва"
    assert data["weather"]["current_weather"]["temperature"] == 23.0
    
    # проверяем что запись в бд создана
    from app.models.history_model import SearchHistory # чтобы избежать циклич зависимостей на уровне модуля
    history_entry = db_session.query(SearchHistory).filter_by(user_id=user_id, city_name="Москва").first()
    assert history_entry is not None
    assert history_entry.country == "Россия"
    
# получение погоды для несуществующего города
async def test_get_weather_city_not_found(client: AsyncClient, mocker):
    city_name = "НеСущетсуетГород228"
    user_id = "test-user"
    cookies = {"user_id": user_id}
    mocker.patch("app.services.open_meteo_service.get_city_coordinates", return_value=None)
    
    client.cookies = cookies
    response = await client.get(f"/api/weather/{city_name}")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Город" in response.json()["detail"] and "не найден" in response.json()["detail"]
    
# тест на успешное получение погоды по точным координатам
async def test_get_weather_lat_on_success(client: AsyncClient, mocker, db_session):
    city_name = "Париж"
    selected_name = "Paris" # из автодопа будет
    selected_admin1 = "Île-de-France"
    selected_country = "France"
    lat, lon = 48.8566, 2.3522
    user_id = "test-user-coords"
    cookies = {"user_id": user_id}
    
    mock_forecast = {"latitude": lat, "longitude": lon, "timezone": "Europe/Paris",
        "current_weather": {"temperature": 18.0, "weathercode": 0, "windspeed": 5.0, "is_day": 1},
        "daily": {"time": ["2025-05-29"], "temperature_2m_max": [20.0], "temperature_2m_min": [12.0], "weathercode": [0],
                  "sunrise": ["2025-05-29T08:00"], "sunset": ["2025-05-29T16:00"],
                  "precipitation_sum": [0.0], "windspeed_10m_max": [7.0]}
    }
    # координаты есть, соответственно, скип get_city_coordonates (в логике на /api/weather так прописано, что если есть коорд, то инфо о городе берется selected_*)
    mocker.patch("app.services.open_meteo_service.get_weather_forecast", return_value=mock_forecast)
    
    url = f"/api/weather/{city_name}?lat={lat}&lon={lon}&selected_name={selected_name}&selected_admin1={selected_admin1}&selected_country={selected_country}"
    client.cookies = cookies
    response = await client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["city_info"]["name"] == selected_name
    assert data["city_info"]["admin1"] == selected_admin1
    assert data["city_info"]["country"] == selected_country
    assert data["weather"]["current_weather"]["temperature"] == 18.0
    
    # проверка записи в бд
    from app.models.history_model import SearchHistory
    history_entry = db_session.query(SearchHistory).filter_by(user_id=user_id, city_name=selected_name, country=selected_country).first() # в бддолжно пойти точное имя
    assert history_entry is not None
    assert history_entry.latitude == lat