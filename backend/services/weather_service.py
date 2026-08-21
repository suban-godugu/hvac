import os
import time
import threading
import logging
import httpx
from typing import Dict, Any

logger = logging.getLogger("weather_service")


def _load_root_env() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    path = os.path.join(root, ".env")
    if not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        return


class LiveWeatherService:
    def __init__(self):
        _load_root_env()
        self.api_key = os.getenv("OPENWEATHER_API_KEY") or None
        self.lat = float(os.getenv("FACILITY_LAT", "12.9716"))
        self.lon = float(os.getenv("FACILITY_LON", "77.5946"))
        self.city_name = os.getenv("FACILITY_CITY", "Bengaluru")
        self.location_name = os.getenv("FACILITY_LOCATION", "Bengaluru, Karnataka, India")
        self.timezone = os.getenv("FACILITY_TIMEZONE", "Asia/Kolkata")
        self.cached_weather = {
            "oat": None,
            "humidity": None,
            "condition": None,
            "source": "UNAVAILABLE",
            "location": self.location_name,
        }
        self._fetched_at = 0.0
        self._inflight = False
        self._lock = threading.Lock()

    def facility(self) -> Dict[str, Any]:
        _load_root_env()
        lat = float(os.getenv("FACILITY_LAT", "12.9716"))
        lon = float(os.getenv("FACILITY_LON", "77.5946"))
        moved = lat != self.lat or lon != self.lon
        self.api_key = os.getenv("OPENWEATHER_API_KEY") or None
        self.lat = lat
        self.lon = lon
        self.city_name = os.getenv("FACILITY_CITY", "Bengaluru")
        self.location_name = os.getenv("FACILITY_LOCATION", "Bengaluru, Karnataka, India")
        self.timezone = os.getenv("FACILITY_TIMEZONE", "Asia/Kolkata")
        self.cached_weather["location"] = self.location_name
        if moved:
            self._fetched_at = 0.0
        return {
            "name": os.getenv("FACILITY_NAME") or "Senatria Corporation",
            "city": self.city_name,
            "location": self.location_name,
            "timezone": self.timezone,
            "lat": self.lat,
            "lon": self.lon,
        }

    def snapshot(self, refresh_seconds: int = 600) -> Dict[str, Any]:
        """Return cached weather immediately; refresh in the background when stale."""
        age = time.time() - self._fetched_at if self._fetched_at else None
        stale = self._fetched_at == 0 or (age is not None and age >= refresh_seconds)
        if stale:
            self._refresh_async()
        payload = dict(self.cached_weather)
        payload["timezone"] = self.timezone
        payload["city"] = self.city_name
        payload["ageSeconds"] = None if age is None else round(age)
        return payload

    def _refresh_async(self) -> None:
        with self._lock:
            if self._inflight:
                return
            self._inflight = True

        def _run():
            try:
                self.fetch_live_weather_sync()
                self._fetched_at = time.time()
            except Exception as exc:
                logger.warning("background weather refresh failed: %s", exc)
            finally:
                with self._lock:
                    self._inflight = False

        threading.Thread(target=_run, daemon=True, name="weather-refresh").start()

    def fetch_live_weather_sync(self) -> Dict[str, Any]:
        """Fetches real-time OAT and RH from OpenWeatherMap (with fallback to Open-Meteo)."""
        if self.api_key:
            try:
                url = f"https://api.openweathermap.org/data/2.5/weather?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"
                resp = httpx.get(url, timeout=4.0)
                if resp.status_code == 200:
                    data = resp.json()
                    main = data.get("main", {})
                    weather_arr = data.get("weather", [{}])
                    self.cached_weather = {
                        "oat": round(float(main.get("temp")), 1) if main.get("temp") is not None else None,
                        "humidity": int(main.get("humidity")) if main.get("humidity") is not None else None,
                        "condition": weather_arr[0].get("main") if weather_arr else None,
                        "source": "OpenWeatherMap Live API",
                        "location": self.location_name,
                    }
                    self._fetched_at = time.time()
                    return self.cached_weather
                logger.warning(f"OpenWeatherMap returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.warning(f"OpenWeatherMap call failed: {e}")

        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={self.lat}&longitude={self.lon}"
                "&current=temperature_2m,relative_humidity_2m"
                f"&timezone={self.timezone.replace(' ', '%20')}"
            )
            resp = httpx.get(url, timeout=4.0)
            if resp.status_code == 200:
                data = resp.json()
                curr = data.get("current", {})
                self.cached_weather = {
                    "oat": round(float(curr["temperature_2m"]), 1) if curr.get("temperature_2m") is not None else None,
                    "humidity": int(curr["relative_humidity_2m"]) if curr.get("relative_humidity_2m") is not None else None,
                    "condition": "Live",
                    "source": "Open-Meteo Live API",
                    "location": self.location_name,
                }
                self._fetched_at = time.time()
                return self.cached_weather
        except Exception as e:
            logger.warning(f"Open-Meteo fallback failed: {e}")

        return self.cached_weather

    async def fetch_live_weather(self) -> Dict[str, Any]:
        return self.fetch_live_weather_sync()

    def forecast(self) -> Dict[str, Any]:
        """Outdoor forecast for O1 (API key never stored in source)."""
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}"
                "&hourly=temperature_2m,relative_humidity_2m&forecast_days=2"
                f"&timezone={self.timezone}"
            )
            resp = httpx.get(url, timeout=6.0)
            if resp.status_code == 200:
                data = resp.json()
                hourly = data.get("hourly") or {}
                return {
                    "source": "Open-Meteo",
                    "timezone": self.timezone,
                    "times": (hourly.get("time") or [])[:24],
                    "temperature_c": (hourly.get("temperature_2m") or [])[:24],
                    "humidity": (hourly.get("relative_humidity_2m") or [])[:24],
                }
        except Exception as e:
            logger.warning("forecast failed: %s", e)
        return {"source": "UNAVAILABLE", "timezone": self.timezone, "times": [], "temperature_c": [], "humidity": []}


weather_service = LiveWeatherService()
