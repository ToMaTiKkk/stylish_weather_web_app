from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Dict, Any, Optional
import uvicorn

# импортируем свои сервисы и WMO_CODES
from .services import open_meteo_service

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
async def read_root(request: Request):
    # отдаем главную страницу
    return templates.TemplateResponse("index.html", {
            "request": request, 
            "app_title": app.title,
            "wmo_codes": open_meteo_service.WMO_CODES
    })

# эндпоинт для получения погоды
@app.get("/api/weather/{city_name}")
async def get_weather_data_for_city(
            city_name: str, 
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
        
    # получаем сам прогноз по определенным координатам
    weather_data = await open_meteo_service.get_weather_forecast(latitude=latitude, longitude=longitude)
    if not weather_data:
        raise HTTPException(status_code=503, detail="Не удалось получить данные о погоде от внешнего сервиса")
        
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
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)