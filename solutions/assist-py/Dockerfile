# Базовый образ
FROM python:3.11-slim
LABEL maintainer="ivanovsky@lab.local"
LABEL version="1.0"
WORKDIR /app
ENV PORT=5451
# Отдельное копирование зависимостей для кеширования
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ ./app/
EXPOSE ${PORT}
# Запуск приложения на персональном порту
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
