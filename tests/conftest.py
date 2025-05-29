import pytest
import asyncio
from typing import AsyncGenerator, Generator
# импорты связанные с бд
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
# импортиры зависимостей приложения
from app.main import app
from app.db.session import Base, get_db
from app.models import history_model

# тестовая бд, а именно in-memory SQLite, чтобы каждый тест был с чистой бд, +к скорости и изоляции
SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///:memory:"
engine_test = create_engine(SQLALCHEMY_DATABASE_URL_TEST, connect_args={"check_same_thread": False})
# таблицы в бд создается один раз
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# фикстура для переопределения зависимости get_db
@pytest.fixture(scope="function") # для каждого тест - новая бд
def db_session() -> Generator[Session, None, None]:
    history_model.Base.metadata.create_all(bind=engine_test)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # удаляем таблицы после каждого из тестов для чистоты и изоляции тестов друг от друга
        history_model.Base.metadata.drop_all(bind=engine_test)
        
# фикстура для async HTTP клиента FastAPI, будет использовать переопределенную сессию БД
@pytest.fixture(scope="function")
async def client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    # зависимость get_db переопределяем под нашу тестовую сессию
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
    
    #очистка после переопределения теста
    del app.dependency_overrides[get_db]