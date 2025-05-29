from fastapi import FastAPI, Request, HTTPException, Query, Depends
from fastapi import Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uvicorn
import uuid

# импортируем свои сервисы и WMO_CODES
from .services import open_meteo_service
from .db import session as db_session # сама сессия и engine
from .db.session import get_db
from .crud import history_crud
from .models import history_model
from .schemas import history_schema

# создание бд (если нет) пока что простой способ без Alembic
history_model.Base.metadata.create_all(bind=db_session.engine)

# чтобы фаст апи корректно находил static and templates, то ему нужно указать базовую директорию проекта
# а именно на родителя main.py, где собственно и есть static and templates
BASE_DIR = Path(__file__).resolve().parent 

app = FastAPI(title="Приложение для погоды", 
                        description="Узнайте погоду в вашем городе в стильном и удобном приложении для погоды", 
                        version="0.1.0")
# сначала путь по которому будут доступны файлы, а потом путь к папке со статикой на сервере
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user_id_cookie: Optional[str] = Cookie(None, alias="user_id")):
    context = {
            "request": request, 
            "app_title": app.title,
            "wmo_codes": open_meteo_service.WMO_CODES
    }
    response = templates.TemplateResponse(request, "index.html", context)
    
    if not user_id_cookie:
        new_user_id  = str(uuid.uuid4())
        # куки доступен из JS (httponly), защита от CSRF (samesite), куки живет год
        response.set_cookie(
                key="user_id",
                value=new_user_id,
                httponly=True,
                samesite="lax",
                max_age=365 * 24 * 60 * 60
        )
        print(f"Установлен новый user_id cookie: {new_user_id}")
    else:
        print(f"Найден существующий user_id cookie: {user_id_cookie}")
    
    return response

# эндпоинт для получения погоды
@app.get("/api/weather/{city_name}")
async def get_weather_data_for_city(
            city_name: str, 
            request: Request, # доступ к куки
            db: Session = Depends(get_db),
            lat: Optional[float] = Query(None), 
            lon: Optional[float] = Query(None),
            selected_name: Optional[str] = Query(None),
            selected_admin1: Optional[str] = Query(None),
            selected_country: Optional[str] = Query(None)):
    # если координаты переданы, то прямое получение погоды по координатам, иначе геокодируется город
    final_city_name = city_name; # имя для отображения и овтета
    latitude = lat
    longitude = lon
    city_details_for_response = {} 
    
    if latitude is not None and longitude is not None:
        # пока что дял простоты в city_info будет то, что передано с фронта, и без страны с регионом
        print(f"Получение погоды по координатам: lat={latitude}, lon={longitude} для города (приблизительно) {city_name}")
        print(f"Детали города из запроса: name='{selected_name}', admin1='{selected_admin1}', country='{selected_country}'")
        
        city_details_for_response = {
            "name": selected_name if selected_name else city_name,
            "admin1": selected_admin1,
            "country": selected_country,
            "latitude": latitude, 
            "longitude": longitude
            }
    else: # если координаты не переданы
        # если пользователь просто ввел город и нажал Enter
        print(f"Координаты не переданы, геокодирование по имени: '{city_name}'")
        if not city_name:
            raise HTTPException(status_code=400, detail="Название города не может быть пустым.")
        
        city_coords = await open_meteo_service.get_city_coordinates(city_name)
        if not city_coords:
            raise HTTPException(status_code=404, detail=f"Город '{city_name}' не найден или произошла ошибка при геокодировании.")
        
        latitude = city_coords["latitude"]
        longitude = city_coords["longitude"]
        #final_city_name = city_coords.get("name", city_name)
        city_details_for_response = city_coords
    
    final_city_name_for_history = city_details_for_response.get("name", city_name)
    # получаем сам прогноз по определенным координатам
    weather_data = await open_meteo_service.get_weather_forecast(latitude=latitude, longitude=longitude)
    if not weather_data:
        raise HTTPException(status_code=503, detail="Не удалось получить данные о погоде от внешнего сервиса")
        
    # запись в историю поиска
    user_id = request.cookies.get("user_id")
    if user_id:
        history_city_name = city_details_for_response.get("name")
        history_admin1 = city_details_for_response.get("admin1")
        history_country = city_details_for_response.get("country")
        
        if history_city_name:
            history_crud.create_search_record(db=db, user_id=user_id, city_name=history_city_name, admin1=history_admin1, country=history_country, latitude=latitude, longitude=longitude)
        else:
            print(f"Warning: Не удалось определить имя города для записи в историю. User: {user_id}, Lat: {latitude}, Lon: {longitude}")
    else:
        print("Warning: user_id cookie не найден, история поиска не будет записана для этого запроса")
    
    # объединяем информацию и городе с погодными условиями (+ для фронта)
    full_response = {
        "city_info":city_details_for_response, # используем или собранные или найденные данный
        "weather": weather_data
    }
    print(f"Отправка ответа с city_info: {city_details_for_response}")
    return JSONResponse(content=full_response)

# для автодопа посика
@app.get("/api/autocomplete/cities", response_model=List[Dict[str, Any]]) # указываем модель ответа для оптимизации
async def autocomplete_city_names(query: str):
    if not query or len(query) < 2:
        return [] # для слишком коротких запросов - пустой список
        
    cities = await open_meteo_service.search_cities_for_autocomplete(query_fragment=query, count=100)
    return cities

# для статистики городов поиска
@app.get("/api/stats/city-searches", response_model=List[history_schema.CitySearchStat])
def get_search_statistics(db: Session = Depends(get_db)):
    stats = history_crud.get_city_search_stats(db=db)
    return stats # так как from_attributes = True, то объекты автоматов преобразуются в pydantic схемы
    
# дл истории поиска текущего пользователя
@app.get("/api/history/user", response_model=List[history_schema.UserHistoryItem])
def get_current_user_history(request: Request, db: Session = Depends(get_db), limit: int = Query(10, ge=1, le=50)): # ограничиваем колво запросов
    user_id = request.cookies.get("user_id")
    if not user_id:
        return [] # пустой список, чтобы на фронте было проще обработать, или же можно полноценно кинутть 401 ошибку, что пользователь не аутентифицирован
    
    user_history_db = history_crud.get_user_search_history(db=db, user_id=user_id, limit=limit)
    return user_history_db
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)