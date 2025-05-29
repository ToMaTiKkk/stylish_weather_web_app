import pytest
from sqlalchemy.orm import Session

from app.crud import history_crud
from app.schemas import history_schema
from app.models import history_model 

def test_create_search_record(db_session: Session):
    user_id = "crud-user-1"
    city_name = "Рим"
    admin1 = "Лацио"
    country = "Италия"
    lat, lon = 41.9028, 12.4964
    
    db_entry = history_crud.create_search_record(db_session, user_id, city_name, admin1, country, lat, lon)
    
    assert db_entry.id is not None
    assert db_entry.user_id == user_id
    assert db_entry.admin1 == admin1
    assert db_entry.country == country
    assert db_entry.latitude == lat
    assert db_entry.longitude == lon
    assert db_entry.search_timestamp is not None
    
    # проверяем что запись действительно есть в бд
    retrieved_entry = db_session.query(history_model.SearchHistory).filter_by(id=db_entry.id).first()
    assert retrieved_entry is not None
    assert retrieved_entry.city_name == city_name
    
def test_get_city_search_stats_empty(db_session: Session):
    stats = history_crud.get_city_search_stats(db_session)
    assert stats == []
    
def test_get_city_search_stats_with_data(db_session: Session):
    history_crud.create_search_record(db_session, "u1", "ГородА", latitude=1.0, longitude=1.0)
    history_crud.create_search_record(db_session, "u2", "ГородБ", latitude=2.0, longitude=2.0)
    history_crud.create_search_record(db_session, "u3", "ГородА", latitude=1.0, longitude=1.0)
    
    stats = history_crud.get_city_search_stats(db_session)
    
    assert len(stats) == 2
    # статистика по убыванию количеству поиска
    assert stats[0].city_name == "ГородА"
    assert stats[0].search_count == 2
    assert stats[1].city_name == "ГородБ"
    assert stats[1].search_count == 1
    
def test_get_user_search_history(db_session: Session):
    user1_id = "user-hist-1"
    user2_id = "user-hist-2"
    history_crud.create_search_record(db_session, user1_id, "Город1_U1", latitude=1.0, longitude=1.0)
    history_crud.create_search_record(db_session, user2_id, "Город1_U2", latitude=2.0, longitude=2.0)
    history_crud.create_search_record(db_session, user1_id, "Город2_U1", latitude=3.0, longitude=3.0) # более поздняя запись для user1
    
    history_u1 = history_crud.get_user_search_history(db_session, user1_id, limit=5)
    assert len(history_u1) == 2
    assert history_u1[0].city_name == "Город2_U1" #последний поиск первый
    assert history_u1[1].city_name == "Город1_U1"

    history_u2 = history_crud.get_user_search_history(db_session, user2_id, limit=5)
    assert len(history_u2) == 1
    assert history_u2[0].city_name == "Город1_U2"

    empty_history = history_crud.get_user_search_history(db_session, "non-existent-user", limit=5)
    assert empty_history == []
