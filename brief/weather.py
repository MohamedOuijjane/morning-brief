"""Today's weather from Open-Meteo (no API key)."""

from typing import Any

from brief import config, utils
from brief.http import get_json

FORECAST_API = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes used by Open-Meteo.
WEATHER_CODES: dict[int, tuple[str, str]] = {
    0: ("Ciel dégagé", "☀️"),
    1: ("Plutôt dégagé", "🌤"),
    2: ("Partiellement nuageux", "⛅"),
    3: ("Couvert", "☁️"),
    45: ("Brouillard", "🌫"),
    48: ("Brouillard givrant", "🌫"),
    51: ("Bruine légère", "🌦"),
    53: ("Bruine", "🌦"),
    55: ("Bruine dense", "🌦"),
    56: ("Bruine verglaçante légère", "🌧"),
    57: ("Bruine verglaçante dense", "🌧"),
    61: ("Pluie faible", "🌧"),
    63: ("Pluie", "🌧"),
    65: ("Forte pluie", "🌧"),
    66: ("Pluie verglaçante légère", "🌧"),
    67: ("Forte pluie verglaçante", "🌧"),
    71: ("Neige faible", "🌨"),
    73: ("Neige", "🌨"),
    75: ("Forte neige", "❄️"),
    77: ("Grains de neige", "🌨"),
    80: ("Averses légères", "🌦"),
    81: ("Averses", "🌧"),
    82: ("Averses violentes", "⛈"),
    85: ("Averses de neige", "🌨"),
    86: ("Fortes averses de neige", "❄️"),
    95: ("Orage", "⛈"),
    96: ("Orage avec grêle", "⛈"),
    99: ("Orage avec forte grêle", "⛈"),
}


def fetch_forecast() -> dict[str, Any]:
    params = {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "timezone": config.TIMEZONE,
        "current": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,wind_speed_10m_max",
        "forecast_days": 1,
    }
    return get_json(FORECAST_API, params=params, label="get_weather")


def get_weather() -> str:
    data = fetch_forecast()
    daily = data["daily"]
    current = data.get("current", {})
    label, icon = WEATHER_CODES.get(daily["weather_code"][0], ("Inconnu", "🌡"))
    n = utils.fr_number
    return "\n".join([
        f"{icon} <b>Météo à {utils.escape(config.CITY_NAME)}</b>",
        label,
        f"Actuellement : {n(current.get('temperature_2m', '?'))} °C",
        f"Min / Max : {n(daily['temperature_2m_min'][0])} °C"
        f" / {n(daily['temperature_2m_max'][0])} °C",
        f"Risque de pluie : {daily['precipitation_probability_max'][0]} %",
        f"Vent : jusqu'à {n(daily['wind_speed_10m_max'][0])} km/h",
    ])
