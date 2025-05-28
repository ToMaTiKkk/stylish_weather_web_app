from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn

# чтобы фаст апи корректно находил static and templates, то ему нужно указать базовую директорию проекта
# а именно на родителя main.py, где собственно и есть static and templates
BASE_DIR = Path(__file__).resolve().parent 

app = FastAPI(title="Приложение для погоды", description="Узнайте погоду в вашем городе в стильном и удобном приложении для погоды", version="0.0.1")
# сначала путь по которому будут доступны файлы, а потом путь к папке со статикой на сервере
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def reaad_root(request: Request):
    # отдаем главную страницу
    return templates.TemplateResponse("index.html", {"request": request, "app_title": app.title})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)