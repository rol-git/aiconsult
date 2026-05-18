"""Nominatim (OSM) — бесплатный геокодер. Лимит 1 RPS, нужна атрибуция."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

import httpx

from geolib.cache import TTLCache

logger = logging.getLogger(__name__)


class NominatimGeocoder:
    """Тонкий клиент над nominatim.openstreetmap.org с кешем и rate-limit."""

    def __init__(self, base_url: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        self.base_url = (base_url or os.getenv("NOMINATIM_BASE_URL") or "https://nominatim.openstreetmap.org").rstrip("/")
        self.user_agent = user_agent or os.getenv("NOMINATIM_USER_AGENT") or "AIConsultTyumen/1.0"
        self._client = httpx.Client(
            timeout=httpx.Timeout(15.0, connect=8.0),
            headers={"User-Agent": self.user_agent, "Accept-Language": "ru"},
        )
        self._lock = threading.Lock()
        self._last_call_ts = 0.0
        self._cache = TTLCache()

    def _throttle(self) -> None:
        """Ниже 1 RPS — Nominatim требует."""
        with self._lock:
            now = time.time()
            wait = 1.05 - (now - self._last_call_ts)
            if wait > 0:
                time.sleep(wait)
            self._last_call_ts = time.time()

    def geocode(self, query: str, *, region_hint: str = "Тюменская область") -> Optional[tuple[float, float]]:
        """Текст → (lat, lon). Возвращает None если не нашло."""
        q = query.strip()
        if not q:
            return None
        # Добавляем регион чтобы притягивать к Тюм. области
        biased = q if region_hint.lower() in q.lower() else f"{q}, {region_hint}"
        cache_key = f"fwd:{biased.lower()}"

        def loader() -> Optional[tuple[float, float]]:
            self._throttle()
            params = {
                "q": biased,
                "format": "json",
                "limit": 1,
                "addressdetails": 0,
                "countrycodes": "ru",
            }
            try:
                resp = self._client.get(f"{self.base_url}/search", params=params)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("Nominatim forward error: %s", exc)
                return None
            data = resp.json()
            if not isinstance(data, list) or not data:
                return None
            try:
                return float(data[0]["lat"]), float(data[0]["lon"])
            except (KeyError, ValueError, TypeError):
                return None

        return self._cache.get_or_load(cache_key, loader, ttl_s=24 * 3600)

    def reverse(self, lat: float, lon: float) -> Optional[str]:
        """(lat, lon) → краткий адрес."""
        cache_key = f"rev:{round(lat, 4)}_{round(lon, 4)}"

        def loader() -> Optional[str]:
            self._throttle()
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json",
                "zoom": 14,
                "addressdetails": 0,
            }
            try:
                resp = self._client.get(f"{self.base_url}/reverse", params=params)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("Nominatim reverse error: %s", exc)
                return None
            data = resp.json() or {}
            return data.get("display_name") or None

        return self._cache.get_or_load(cache_key, loader, ttl_s=6 * 3600)
