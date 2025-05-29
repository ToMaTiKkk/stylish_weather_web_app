from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# бд в корне проекта
SQLALCHEMY_DATABASE_URL = "sqlite:///./stylish_weather_app_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}) # единый поток для запроса
# фабрика для сессий бд
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try: 
        yield db # предоставляем сессию
    finally:
        db.close()