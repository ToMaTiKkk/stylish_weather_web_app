from sqlalchemy import Column, Integer, String, DateTime, func, Float
from ..db.session import Base

class SearchHistory(Base):
    __tablename__ = "search_history" # назавание таблицы в бд
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False) # из куки
    city_name = Column(String, index=True, nullable=False)
    admin1 = Column(String, nullable=True)
    country = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    # время автоматом при создании записи
    search_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return (f"<SearchHistory(user_id='{self.user_id}', "
                f"city='{self.city_name}', admin1='{self.admin1}', country='{self.country}', "
                f"lat={self.latitude}, lon={self.longitude})>")