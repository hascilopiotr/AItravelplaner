"""
Daily weather forecast from Open-Meteo (free, no API key).
Only dates within the forecast range (~16 days ahead) get a forecast; failures
return {} so planning works without weather.
"""

from __future__ import annotations

from datetime import date

import requests

from data.osm_fetcher import HEADERS

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 16

# WMO weather codes -> (emoji, label)
_WMO = {
    0: ("☀️", "Clear"), 1: ("🌤️", "Mostly clear"), 2: ("⛅", "Partly cloudy"), 3: ("☁️", "Overcast"),
    45: ("🌫️", "Fog"), 48: ("🌫️", "Freezing fog"),
    51: ("🌦️", "Light drizzle"), 53: ("🌦️", "Drizzle"), 55: ("🌧️", "Heavy drizzle"),
    56: ("🌧️", "Freezing drizzle"), 57: ("🌧️", "Freezing drizzle"),
    61: ("🌦️", "Light rain"), 63: ("🌧️", "Rain"), 65: ("🌧️", "Heavy rain"),
    66: ("🌧️", "Freezing rain"), 67: ("🌧️", "Freezing rain"),
    71: ("🌨️", "Light snow"), 73: ("🌨️", "Snow"), 75: ("❄️", "Heavy snow"), 77: ("🌨️", "Snow grains"),
    80: ("🌦️", "Rain showers"), 81: ("🌧️", "Rain showers"), 82: ("⛈️", "Violent showers"),
    85: ("🌨️", "Snow showers"), 86: ("❄️", "Heavy snow showers"),
    95: ("⛈️", "Thunderstorm"), 96: ("⛈️", "Thunderstorm, hail"), 99: ("⛈️", "Thunderstorm, hail"),
}


def describe(code: int | None) -> tuple[str, str]:
    return _WMO.get(code, ("🌡️", "Unknown"))


def get_forecast(lat: float, lon: float, dates: list[str]) -> dict[str, dict]:
    """
    Returns {iso_date: {code, emoji, label, tmin, tmax, rain_prob}} for the requested
    dates that fall inside the forecast window. Never raises.
    """
    today = date.today()
    wanted = [d for d in dates if 0 <= (date.fromisoformat(d) - today).days < FORECAST_DAYS]
    if not wanted:
        return {}
    try:
        resp = requests.get(FORECAST_URL, params={
            "latitude": lat, "longitude": lon, "timezone": "auto",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "start_date": min(wanted), "end_date": max(wanted),
        }, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        daily = resp.json()["daily"]
    except Exception:
        return {}

    out = {}
    for i, iso in enumerate(daily.get("time", [])):
        if iso not in wanted:
            continue
        code = daily["weather_code"][i]
        emoji, label = describe(code)
        out[iso] = {
            "code": code, "emoji": emoji, "label": label,
            "tmin": daily["temperature_2m_min"][i], "tmax": daily["temperature_2m_max"][i],
            "rain_prob": daily["precipitation_probability_max"][i],
        }
    return out


def weather_text(w: dict | None, emoji: bool = True) -> str:
    """'🌧️ Rain · 2–6 °C · rain 80%' (or without emoji, for the PDF/prompt)."""
    if not w:
        return "no forecast yet"
    parts = [f"{w['emoji']} {w['label']}" if emoji else w["label"]]
    if w.get("tmin") is not None and w.get("tmax") is not None:
        parts.append(f"{w['tmin']:.0f} to {w['tmax']:.0f} °C")
    if w.get("rain_prob") is not None:
        parts.append(f"rain {w['rain_prob']:.0f}%")
    return " · ".join(parts)
