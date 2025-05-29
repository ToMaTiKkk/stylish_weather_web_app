FROM python:3.10-slim
WORKDIR /app

# установка перменных окружения, первое - гарант, что логи и принты в контейнер попадают
# второе - предотвращает сохран .pyc файлов в контейнере, экономим место
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# докер кэширует слой, файл не изменился - переустановки зависимостей при каждом запуске не будет
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]