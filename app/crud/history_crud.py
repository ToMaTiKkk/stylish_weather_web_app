from sqlalchemy.orm import Session
from sqlalchemy import func, desc # для count, для сортировки
from typing import List, Optional

from ..models import history_model
from ..schemas import history_schema

# создает новую запись в истории поиска
# возвращает созданный объект типа SearchHistory
def create_search_record(db: Session, user_id: str, city_name: str, admin1: Optional[str] = None, country: Optional[str] = None, latitude: Optional[float] = None, longitude: Optional[float] = None) -> history_model.SearchHistory:
    db_search_entry = history_model.SearchHistory(user_id=user_id, city_name=city_name, admin1=admin1, country=country, latitude=latitude, longitude=longitude)
    db.add(db_search_entry)
    db.commit()
    db.refresh(db_search_entry) # обновляем объект из дб чтобы получить id и время сохрана
    print(f"Запись в историю: User {user_id} искал {city_name}, {admin1}, {country} (lat:{latitude}, lon:{longitude})")
    return db_search_entry
 
# получаем статистику поисков для каждого города, сортируется по кол-ву поисков   
# возвращает список объектов типа CitySearchStat
def get_city_search_stats(db: Session) -> List[history_schema.CitySearchStat]:
    # запрос с группировкой и подсчетом
    query_results = db.query(
            history_model.SearchHistory.city_name,
            # для подсчета, для псевдонима колонки
            func.count(history_model.SearchHistory.id).label("search_count")
            ).group_by(history_model.SearchHistory.city_name).order_by(desc("search_count")).all()
    # аналог SQL запрос: SELECT city_name, COUNT(id) as search_count FROM search_history GROUP BY city_name ORDER BY search_count DESC
    
    # преобразуем рез в списко pydantic схем
    stats = []
    for city, count in query_results:
        stats.append(history_schema.CitySearchStat(city_name=city, search_count=count))
    print(f"Статистика по городам: {stats}")
    return stats

# получает последние N записи поиска для конкретного пользователя и возвращает списков объектов типа SearchHistory    
def get_user_search_history(db: Session, user_id: str, limit: int = 10) -> List[history_model.SearchHistory]:
    # если время одинаково, то записи сортируются по id в убывающем порядке, тот, кто позже вставлен, у того айди и больше и при сортировке будет первым
    history_entries = db.query(history_model.SearchHistory).filter(history_model.SearchHistory.user_id == user_id).order_by(desc(history_model.SearchHistory.search_timestamp), desc(history_model.SearchHistory.id)).limit(limit).all()
    return history_entries