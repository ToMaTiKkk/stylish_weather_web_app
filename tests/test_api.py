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
    client.cookies.update(cookies)
    response1 = await client.get("/")
    assert response1.status_code == status.HTTP_200_OK
    # если куки уже есть, то UUID перезаписывать не должен
    assert "user_id" not in response1.cookies
    
    # сделаем на всякий и второй такой же запрос
    response2 = await client.get("/")
    assert response2.status_code == status.HTTP_200_OK
    assert "user_id" not in response2.cookies
    
    # после тестов куки очищаем
    client.cookies.clear()