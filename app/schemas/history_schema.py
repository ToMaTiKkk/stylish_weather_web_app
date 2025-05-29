from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime
from typing import Optional

# схема отображения статистики по городам
class CitySearchStat(BaseModel):
    city_name: str
    search_count: int
    
    model_config = ConfigDict(from_attributes=True)
        
# схема для отображения одной записи в истории пользователя
class UserHistoryItem(BaseModel):
    city_name: str
    search_timestamp: datetime
    admin1: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)