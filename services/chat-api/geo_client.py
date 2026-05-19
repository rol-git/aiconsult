"""HTTP-клиент к geo-service. Подменяет старый GeoService в монолите.

Тот же интерфейс, что был у GeoService: build_geo_card, geocode_address, list_pvr_in_district.
При сетевых ошибках возвращает пустую/безопасную карточку — geo_agent умеет с этим работать.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from geo.models import GeoCard, PVR, UserLocation

logger = logging.getLogger(__name__)


class GeoHttpClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def build_geo_card(self, location: UserLocation) -> GeoCard:
        params = {"lat": location.lat, "lon": location.lon, "source": location.source}
        if location.accuracy_m is not None:
            params["accuracy"] = location.accuracy_m
        try:
            resp = httpx.get(f"{self._base}/profile", params=params, timeout=self._timeout)
            resp.raise_for_status()
            return GeoCard.from_dict(resp.json()["profile"])
        except Exception as exc:
            logger.warning("geo-service /profile failed: %s", exc)
            return GeoCard(
                location=location,
                in_tyumen=False,
                nearest_pvrs=[],
                flood=None,
                blocked_roads_nearby=0,
                nearest_hydropost_km=None,
                notes=["geo-service временно недоступен"],
            )

    def geocode_address(self, text: str) -> Optional[UserLocation]:
        try:
            resp = httpx.get(f"{self._base}/geocode", params={"q": text}, timeout=self._timeout)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json().get("location")
            return UserLocation.from_dict(data) if data else None
        except Exception as exc:
            logger.warning("geo-service /geocode failed: %s", exc)
            return None

    def list_pvr_in_district(self, district: str) -> List[PVR]:
        try:
            resp = httpx.get(
                f"{self._base}/pvr",
                params={"district": district},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return [PVR.from_dict(item) for item in resp.json().get("items", [])]
        except Exception as exc:
            logger.warning("geo-service /pvr failed: %s", exc)
            return []
