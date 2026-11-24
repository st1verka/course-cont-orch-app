from contextlib import asynccontextmanager, closing
from fastapi import FastAPI, HTTPException
import psycopg2
from pydantic import BaseModel
import os
import httpx

DATABASE_URL = os.getenv("DATABASE_URL")


def connect():
    return psycopg2.connect(DATABASE_URL, connect_timeout=3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DATABASE_URL:
        with closing(connect()) as connection:
            with connection, connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id BIGSERIAL PRIMARY KEY,
                        text TEXT NOT NULL
                    )
                """)
    yield


app = FastAPI(title="Personal Assistant", lifespan=lifespan)

OWNER = os.getenv("APP_OWNER", "anonymous")
SECRET_KEY = os.getenv("APP_SECRET", "default_secret")


class Note(BaseModel):
    text: str


notes: list[str] = []


@app.get("/")
async def root():
    return {
        "message": f"👋 Привет, {OWNER}!",
        "service": "personal-assistant",
        "version": "1.0",
        "endpoints": ["/me", "/notes", "/weather/{city}", "/secret/{key}"],
    }


@app.get("/health")
def health():
    if not DATABASE_URL:
        return {"status": "healthy", "owner": OWNER}

    try:
        with closing(connect()) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except psycopg2.Error as error:
        raise HTTPException(503, "PostgreSQL is unavailable") from error

    return {"status": "healthy", "owner": OWNER, "database": "connected"}


@app.get("/me")
async def me():
    return {
        "owner": OWNER,
        "secret_prefix": SECRET_KEY[:6]
        if SECRET_KEY != "default_secret"
        else "NOT_SET",
    }


@app.get("/secret/{key}")
async def secret(key: str):
    """Secret endpoint - checking environment variables"""
    if key == SECRET_KEY:
        return {
            "flag": f"LAB2_SUCCESS_{OWNER.upper()}",
            "message": "The secret key is correct!",
        }
    return {
        "error": "The secret key is incorrect",
        "hint": "Check the APP_SECRET environment variable",
    }


WEATHER_CODES: dict[int, str] = {
    0: "☀️ Ясно", 1: "🌤 Малооблачно", 2: "⛅ Переменная облачность",
    3: "☁️ Пасмурно", 45: "🌫 Туман", 48: "🌫 Изморозь",
    51: "🌦 Лёгкая морось", 53: "🌦 Морось", 55: "🌧 Сильная морось",
    61: "🌧 Небольшой дождь", 63: "🌧 Дождь", 65: "🌧 Сильный дождь",
    71: "🌨 Небольшой снег", 73: "🌨 Снег", 75: "❄️ Сильный снег",
    80: "🌦 Ливень", 81: "🌧 Сильный ливень", 82: "⛈ Штормовой ливень",
    95: "⛈ Гроза", 96: "⛈ Гроза с градом", 99: "⛈ Сильная гроза с градом",
}


@app.get("/weather/{city}")
async def weather(city: str):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            geo_resp = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "ru"},
            )
            geo_data = geo_resp.json()

            if not geo_data.get("results"):
                return {"error": f"City «{city}» not found"}

            location = geo_data["results"][0]
            lat = location["latitude"]
            lon = location["longitude"]
            city_name = location.get("name", city)
            country = location.get("country", "")

            weather_resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                },
            )
            weather_data = weather_resp.json()["current"]

            code = weather_data.get("weather_code", -1)

            return {
                "city": city_name,
                "country": country,
                "coordinates": {"lat": lat, "lon": lon},
                "temperature_c": weather_data["temperature_2m"],
                "humidity_pct": weather_data["relative_humidity_2m"],
                "wind_km_h": weather_data["wind_speed_10m"],
                "condition": WEATHER_CODES.get(code, f"Code {code}"),
            }
    except Exception as e:
        return {"error": f"Failed to get weather: {type(e).__name__}: {e}"}


@app.post("/notes")
def create_note(note: Note):
    if DATABASE_URL:
        with closing(connect()) as connection:
            with connection, connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO notes (text) VALUES (%s) RETURNING id",
                    (note.text,),
                )
                note_id = cursor.fetchone()[0] - 1
                cursor.execute("SELECT COUNT(*) FROM notes")
                total = cursor.fetchone()[0]
        return {"status": "saved", "note_id": note_id, "total": total}

    notes.append(note.text)
    return {"status": "saved", "note_id": len(notes) - 1, "total": len(notes)}


@app.get("/notes")
def list_notes():
    if DATABASE_URL:
        with closing(connect()) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT text FROM notes ORDER BY id")
            saved_notes = [row[0] for row in cursor.fetchall()]
        return {"notes": saved_notes, "count": len(saved_notes)}

    return {"notes": notes, "count": len(notes)}

