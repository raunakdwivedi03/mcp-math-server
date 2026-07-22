# weather_tools.py — Current weather & forecast (Open-Meteo zero-config fallback + OpenWeatherMap support)
from __future__ import annotations
import os
import requests
from fastmcp import FastMCP

mcp = FastMCP("weather")

API_KEY_ENV = "OPENWEATHERMAP_API_KEY"
OWM_BASE_URL = "https://api.openweathermap.org/data/2.5"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather interpretation codes (Open-Meteo)
WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Slight rain showers",
    81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm"
}


def _geocode_city(city: str) -> dict:
    """Geocode a city name using Open-Meteo API with fallback for multi-part names like 'Gurgaon, Haryana'."""
    geo_resp = requests.get(GEOCODE_URL, params={"name": city, "count": 1}, timeout=10)
    geo_resp.raise_for_status()
    geo_data = geo_resp.json()

    if not geo_data.get("results") and "," in city:
        primary_city = city.split(",")[0].strip()
        geo_resp = requests.get(GEOCODE_URL, params={"name": primary_city, "count": 1}, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

    if not geo_data.get("results"):
        raise ValueError(f"Could not find coordinates for city: '{city}'")

    return geo_data["results"][0]


def _get_open_meteo_weather(city: str) -> dict:
    """Fetch current weather from Open-Meteo (requires no API key)."""
    loc = _geocode_city(city)
    lat, lon = loc["latitude"], loc["longitude"]
    city_name = loc.get("name", city)
    country = loc.get("country", "")

    w_resp = requests.get(
        OPEN_METEO_URL,
        params={"latitude": lat, "longitude": lon, "current_weather": True},
        timeout=10,
    )
    w_resp.raise_for_status()
    w_data = w_resp.json()["current_weather"]

    code = w_data.get("weathercode", 0)
    description = WEATHER_CODES.get(code, "Clear")

    return {
        "city": city_name,
        "country": country,
        "temp_c": w_data["temperature"],
        "feels_like_c": w_data["temperature"],
        "humidity_pct": "N/A",
        "wind_kph": w_data["windspeed"],
        "description": description,
        "source": "Open-Meteo (Zero-Config)",
    }


def _get_open_meteo_forecast(city: str, days: int = 3) -> dict:
    """Fetch multi-day forecast from Open-Meteo (requires no API key)."""
    loc = _geocode_city(city)
    lat, lon = loc["latitude"], loc["longitude"]
    city_name = loc.get("name", city)

    days = max(1, min(days, 7))
    w_resp = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,weathercode",
            "timezone": "auto",
        },
        timeout=10,
    )
    w_resp.raise_for_status()
    daily = w_resp.json()["daily"]

    forecast = []
    for i in range(min(days, len(daily["time"]))):
        code = daily["weathercode"][i]
        forecast.append({
            "date": daily["time"][i],
            "high_c": daily["temperature_2m_max"][i],
            "low_c": daily["temperature_2m_min"][i],
            "condition": WEATHER_CODES.get(code, "Clear"),
        })

    return {"city": city_name, "forecast": forecast, "source": "Open-Meteo (Zero-Config)"}


@mcp.tool()
def get_weather(city: str) -> dict:
    """Get current weather for a city.

    Uses OpenWeatherMap if OPENWEATHERMAP_API_KEY is configured in .env,
    otherwise automatically falls back to Open-Meteo (no API key required).
    """
    key = os.getenv(API_KEY_ENV, "").strip()
    if key:
        try:
            resp = requests.get(
                f"{OWM_BASE_URL}/weather",
                params={"q": city, "appid": key, "units": "metric"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "city": data.get("name"),
                "country": data.get("sys", {}).get("country"),
                "temp_c": data["main"]["temp"],
                "feels_like_c": data["main"]["feels_like"],
                "humidity_pct": data["main"]["humidity"],
                "wind_kph": round(data["wind"]["speed"] * 3.6, 1),
                "description": data["weather"][0]["description"],
                "source": "OpenWeatherMap",
            }
        except Exception:
            pass

    return _get_open_meteo_weather(city)


@mcp.tool()
def get_forecast(city: str, days: int = 3) -> dict:
    """Get multi-day weather forecast for a city (max 5 days).

    Uses OpenWeatherMap if OPENWEATHERMAP_API_KEY is configured in .env,
    otherwise automatically falls back to Open-Meteo (no API key required).
    """
    key = os.getenv(API_KEY_ENV, "").strip()
    if key:
        try:
            days = max(1, min(days, 5))
            resp = requests.get(
                f"{OWM_BASE_URL}/forecast",
                params={"q": city, "appid": key, "units": "metric", "cnt": days * 8},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            daily: dict[str, list] = {}
            for entry in data["list"]:
                date = entry["dt_txt"].split(" ")[0]
                daily.setdefault(date, []).append(entry)

            forecast = []
            for date, entries in list(daily.items())[:days]:
                temps = [e["main"]["temp"] for e in entries]
                descriptions = [e["weather"][0]["description"] for e in entries]
                main_desc = max(set(descriptions), key=descriptions.count)
                forecast.append({
                    "date": date,
                    "high_c": round(max(temps), 1),
                    "low_c": round(min(temps), 1),
                    "condition": main_desc,
                })

            return {"city": data["city"]["name"], "forecast": forecast, "source": "OpenWeatherMap"}
        except Exception:
            pass

    return _get_open_meteo_forecast(city, days)
