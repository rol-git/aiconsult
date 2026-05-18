"""HTTP-клиент к OrbisMap (gis.72to.ru). Публичный API, без авторизации."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _build_client() -> httpx.Client:
    proxy = (os.getenv("ORBISMAP_PROXY_URL") or "").strip() or None
    proxies = {"http://": proxy, "https://": proxy} if proxy else None
    return httpx.Client(
        timeout=httpx.Timeout(90.0, connect=15.0, read=90.0),
        headers={"User-Agent": "AIConsultTyumen/1.0"},
        proxies=proxies,
    )


class OrbismapClient:
    """Тонкая обёртка над OrbisMap REST API."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or os.getenv("ORBISMAP_BASE_URL") or "").rstrip("/")
        if not self.base_url:
            raise ValueError("ORBISMAP_BASE_URL не задан")
        self._client = _build_client()

    def list_layers(self) -> List[Dict[str, Any]]:
        return self._get_json("/layers/")

    def layer_structure(self, code: str) -> List[Dict[str, Any]]:
        return self._get_json(f"/layers/{code}/structure/")

    def layer_objects_geojson(
        self,
        code: str,
        *,
        fields: Optional[List[str]] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"format": "geojson", "limit": limit, "offset": offset}
        if fields:
            params["fields"] = ",".join(fields)
        return self._get_json(f"/layers/{code}/objects/", params=params)

    def layer_objects_json(
        self,
        code: str,
        *,
        fields: Optional[List[str]] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if fields:
            params["fields"] = ",".join(fields)
        return self._get_json(f"/layers/{code}/objects/", params=params)

    def _get_json(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        response = self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()
