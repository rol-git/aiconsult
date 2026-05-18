"""GeoService — фасад над OrbisMap + spatial + геокодер.

Кеширует слои OrbisMap, на их основе быстро отвечает на пространственные
запросы: ближайшие ПВР, попадает ли точка в зону подтопления, итд.
"""

from __future__ import annotations

import logging
import threading
from typing import Iterable, List, Optional, Tuple

from geo.cache import TTLCache
from geo.geocoder import NominatimGeocoder
from geo.maps_links import build_route_pair, dgis_point_url, yandex_point_url
from geo.models import (
    FloodCheck,
    GeoCard,
    HydroPost,
    MapLinks,
    NearestPVR,
    PVR,
    RoadPoint,
    UserContext,
    UserLocation,
)
from geo.orbismap_client import OrbismapClient
from geo.spatial import (
    _SpatialFeature,
    feature_from_geojson,
    nearest_points_by_distance,
    nearest_polygon_km,
    point_in_any,
    haversine_km,
)
from geo.tyumen_boundary import is_in_tyumen

logger = logging.getLogger(__name__)


# Слои на карте gis.72to.ru/orbismap/.../map29/
LAYER_PVR = "virtual4"
LAYER_HYDROPOST = "virtual6"
LAYER_ROAD_BLOCKED = "virtual1"
LAYER_ROAD_OPEN = "virtual"
LAYER_HUMANITARIAN = "virtual5"

# Полигональные слои разбиты по 5 территориальным кластерам.
# Суффиксы: "" Ялуторовский/Упоровский/Заводоуковск, "1" Ишимский/Казанский,
# "2" Абатский/Викуловский, "3" Тобольский, "4" Тюменский+Тюмень.
FLOOD_MAX_LAYERS = [
    "maksimalnye_granicy_podtoplenija",
    "maksimalnye_granicy_podtoplenija1",
    "maksimalnye_granicy_podtoplenija2",
    "maksimalnye_granicy_podtoplenija3",
    "maksimalnye_granicy_podtoplenija4",
]
FLOOD_CLEAN_LAYERS = [
    "chistoe_zatoplenie",
    "chistoe_zatoplenie1",
    "chistoe_zatoplenie2",
    "chistoe_zatoplenie3",
    "chistoe_zatoplenie4",
]
FLOOD_CLUSTER_NAMES = {
    "maksimalnye_granicy_podtoplenija": "Ялуторовский/Упоровский/Заводоуковск",
    "maksimalnye_granicy_podtoplenija1": "Ишимский/Казанский",
    "maksimalnye_granicy_podtoplenija2": "Абатский/Викуловский",
    "maksimalnye_granicy_podtoplenija3": "Тобольский",
    "maksimalnye_granicy_podtoplenija4": "Тюменский район и Тюмень",
    "chistoe_zatoplenie": "Ялуторовский/Упоровский/Заводоуковск",
    "chistoe_zatoplenie1": "Ишимский/Казанский",
    "chistoe_zatoplenie2": "Абатский/Викуловский",
    "chistoe_zatoplenie3": "Тобольский",
    "chistoe_zatoplenie4": "Тюменский район и Тюмень",
}

# TTL разных слоёв
TTL_PVR_S = 6 * 3600
TTL_HUMANITARIAN_S = 6 * 3600
TTL_HYDROPOST_S = 30 * 60
TTL_ROADS_S = 15 * 60
TTL_FLOOD_S = 15 * 60


class GeoService:
    """Главный сервис гео-слоя приложения."""

    def __init__(self, orbismap: Optional[OrbismapClient] = None, geocoder: Optional[NominatimGeocoder] = None) -> None:
        self.orbismap = orbismap or OrbismapClient()
        self.geocoder = geocoder or NominatimGeocoder()
        self._cache = TTLCache()

    # ---------- Загрузчики слоёв (с кешем) ----------

    def _load_pvr_features(self) -> List[_SpatialFeature]:
        def loader() -> List[_SpatialFeature]:
            data = self.orbismap.layer_objects_geojson(
                LAYER_PVR,
                fields=["name", "mr", "nas", "adres_pvr", "phone", "vmestimost_chel", "otvet"],
                limit=500,
            )
            feats = []
            for f in data.get("features", []) or []:
                sp = feature_from_geojson(f)
                if sp:
                    feats.append(sp)
            return feats
        return self._cache.get_or_load("pvr", loader, ttl_s=TTL_PVR_S)

    def _load_hydroposts(self) -> List[_SpatialFeature]:
        def loader() -> List[_SpatialFeature]:
            data = self.orbismap.layer_objects_geojson(LAYER_HYDROPOST, limit=200)
            return [f for f in (feature_from_geojson(x) for x in data.get("features", [])) if f]
        return self._cache.get_or_load("hydropost", loader, ttl_s=TTL_HYDROPOST_S)

    def _load_blocked_roads(self) -> List[_SpatialFeature]:
        def loader() -> List[_SpatialFeature]:
            data = self.orbismap.layer_objects_geojson(LAYER_ROAD_BLOCKED, limit=200)
            return [f for f in (feature_from_geojson(x) for x in data.get("features", [])) if f]
        return self._cache.get_or_load("roads_blocked", loader, ttl_s=TTL_ROADS_S)

    def _load_humanitarian(self) -> List[_SpatialFeature]:
        def loader() -> List[_SpatialFeature]:
            data = self.orbismap.layer_objects_geojson(
                LAYER_HUMANITARIAN,
                limit=200,
            )
            return [f for f in (feature_from_geojson(x) for x in data.get("features", [])) if f]
        return self._cache.get_or_load("humanitarian", loader, ttl_s=TTL_HUMANITARIAN_S)

    def _load_flood_layer(self, code: str) -> List[_SpatialFeature]:
        def loader() -> List[_SpatialFeature]:
            # Полигоны бывают тяжёлые — фильтруем только геометрию, без атрибутов
            data = self.orbismap.layer_objects_geojson(code, fields=[], limit=1000)
            return [f for f in (feature_from_geojson(x) for x in data.get("features", [])) if f]
        return self._cache.get_or_load(f"flood:{code}", loader, ttl_s=TTL_FLOOD_S)

    def prewarm(self) -> None:
        """Прогревает критичные слои (ПВР). Зовётся в фоне при старте сервера."""
        try:
            self._load_pvr_features()
        except Exception as exc:
            logger.warning("prewarm PVR failed: %s", exc)

    def _load_all_flood_max(self) -> List[Tuple[str, List[_SpatialFeature]]]:
        out = []
        for code in FLOOD_MAX_LAYERS:
            try:
                out.append((code, self._load_flood_layer(code)))
            except Exception as exc:
                logger.warning("Не удалось загрузить слой %s: %s", code, exc)
        return out

    def _load_all_flood_clean(self) -> List[Tuple[str, List[_SpatialFeature]]]:
        out = []
        for code in FLOOD_CLEAN_LAYERS:
            try:
                out.append((code, self._load_flood_layer(code)))
            except Exception as exc:
                logger.warning("Не удалось загрузить слой %s: %s", code, exc)
        return out

    # ---------- Высокоуровневые операции ----------

    def find_nearest_pvr(
        self,
        lat: float,
        lon: float,
        k: int = 3,
        max_km: float = 300.0,
    ) -> List[NearestPVR]:
        features = self._load_pvr_features()
        ranked = nearest_points_by_distance(lat, lon, features, k=k, max_km=max_km)
        result: List[NearestPVR] = []
        for feat, dist_km in ranked:
            props = feat.properties or {}
            pvr = PVR(
                pvr_id=feat.id,
                name=str(props.get("name") or "ПВР").strip(),
                address=str(props.get("adres_pvr") or "").strip(),
                district=str(props.get("mr") or "").strip(),
                settlement=str(props.get("nas") or "").strip(),
                phone=str(props.get("phone") or "").strip(),
                capacity=str(props.get("vmestimost_chel") or "").strip() or None,
                lat=feat.centroid_lat,
                lon=feat.centroid_lon,
            )
            pair = build_route_pair(lat, lon, pvr.lat, pvr.lon, mode="auto")
            links = MapLinks(yandex=pair["yandex"], dgis=pair["dgis"])
            result.append(NearestPVR(pvr=pvr, distance_km=dist_km, links=links))
        return result

    def list_pvr_in_district(self, district_query: str) -> List[PVR]:
        features = self._load_pvr_features()
        q = district_query.strip().lower()
        if not q:
            return []
        out: List[PVR] = []
        for feat in features:
            props = feat.properties or {}
            mr = str(props.get("mr") or "").lower()
            nas = str(props.get("nas") or "").lower()
            if q in mr or q in nas:
                out.append(
                    PVR(
                        pvr_id=feat.id,
                        name=str(props.get("name") or "ПВР").strip(),
                        address=str(props.get("adres_pvr") or "").strip(),
                        district=str(props.get("mr") or "").strip(),
                        settlement=str(props.get("nas") or "").strip(),
                        phone=str(props.get("phone") or "").strip(),
                        capacity=str(props.get("vmestimost_chel") or "").strip() or None,
                        lat=feat.centroid_lat,
                        lon=feat.centroid_lon,
                    )
                )
        return out

    def check_flood_risk(self, lat: float, lon: float) -> FloodCheck:
        in_max = False
        in_clean = False
        nearest_km: Optional[float] = None
        nearest_district: Optional[str] = None

        for code, feats in self._load_all_flood_max():
            hit = point_in_any(lat, lon, feats)
            if hit is not None:
                in_max = True
                nearest_km = 0.0
                nearest_district = FLOOD_CLUSTER_NAMES.get(code)
                break

        for code, feats in self._load_all_flood_clean():
            hit = point_in_any(lat, lon, feats)
            if hit is not None:
                in_clean = True
                nearest_km = 0.0
                if not nearest_district:
                    nearest_district = FLOOD_CLUSTER_NAMES.get(code)
                break

        if not (in_max or in_clean):
            best: Optional[Tuple[str, float]] = None
            for code, feats in self._load_all_flood_max():
                res = nearest_polygon_km(lat, lon, feats)
                if res is None:
                    continue
                _, d = res
                if best is None or d < best[1]:
                    best = (code, d)
            if best:
                nearest_km = best[1]
                nearest_district = FLOOD_CLUSTER_NAMES.get(best[0])

        return FloodCheck(
            in_max_zone=in_max,
            in_clean_zone=in_clean,
            nearest_zone_km=nearest_km,
            nearest_zone_district=nearest_district,
        )

    def blocked_roads_within(self, lat: float, lon: float, radius_km: float = 10.0) -> List[RoadPoint]:
        feats = self._load_blocked_roads()
        out: List[RoadPoint] = []
        for f in feats:
            d = haversine_km(lat, lon, f.centroid_lat, f.centroid_lon)
            if d <= radius_km:
                out.append(
                    RoadPoint(
                        point_id=f.id,
                        kind="blocked",
                        lat=f.centroid_lat,
                        lon=f.centroid_lon,
                        properties=f.properties,
                    )
                )
        return out

    def nearest_hydropost(self, lat: float, lon: float) -> Optional[Tuple[HydroPost, float]]:
        feats = self._load_hydroposts()
        if not feats:
            return None
        best: Optional[Tuple[_SpatialFeature, float]] = None
        for f in feats:
            d = haversine_km(lat, lon, f.centroid_lat, f.centroid_lon)
            if best is None or d < best[1]:
                best = (f, d)
        if not best:
            return None
        feat, d = best
        return (
            HydroPost(
                post_id=feat.id,
                lat=feat.centroid_lat,
                lon=feat.centroid_lon,
                properties=feat.properties,
            ),
            d,
        )

    def geocode_address(self, text: str) -> Optional[UserLocation]:
        coords = self.geocoder.geocode(text)
        if not coords:
            return None
        lat, lon = coords
        return UserLocation(lat=lat, lon=lon, accuracy_m=None, source="geocoded")

    # ---------- Гео-карточка ----------

    def build_geo_card(
        self,
        location: Optional[UserLocation],
        *,
        pvr_count: int = 3,
    ) -> GeoCard:
        if location is None:
            return GeoCard(
                location=None,
                in_tyumen=False,
                nearest_pvrs=[],
                flood=None,
                blocked_roads_nearby=0,
                nearest_hydropost_km=None,
                notes=["Координаты пользователя не предоставлены."],
            )

        in_tyu = is_in_tyumen(location.lat, location.lon)
        notes: List[str] = []
        if not in_tyu:
            notes.append("Координаты пользователя вне Тюменской области. Спросите адрес или предупредите о покрытии.")

        nearest_pvrs: List[NearestPVR] = []
        flood: Optional[FloodCheck] = None
        blocked = 0
        hydro_km: Optional[float] = None

        try:
            nearest_pvrs = self.find_nearest_pvr(location.lat, location.lon, k=pvr_count)
        except Exception as exc:
            logger.warning("nearest_pvrs failed: %s", exc)
            notes.append("Не удалось загрузить ПВР (карта недоступна).")

        if in_tyu:
            try:
                flood = self.check_flood_risk(location.lat, location.lon)
            except Exception as exc:
                logger.warning("flood_check failed: %s", exc)

            try:
                blocked = len(self.blocked_roads_within(location.lat, location.lon, radius_km=10.0))
            except Exception as exc:
                logger.warning("blocked_roads failed: %s", exc)

            try:
                hp = self.nearest_hydropost(location.lat, location.lon)
                if hp:
                    hydro_km = hp[1]
            except Exception as exc:
                logger.warning("hydropost failed: %s", exc)

        address_label: Optional[str] = None
        try:
            address_label = self.geocoder.reverse(location.lat, location.lon)
        except Exception as exc:
            logger.warning("reverse geocode failed: %s", exc)

        return GeoCard(
            location=location,
            in_tyumen=in_tyu,
            nearest_pvrs=nearest_pvrs,
            flood=flood,
            blocked_roads_nearby=blocked,
            nearest_hydropost_km=hydro_km,
            address_label=address_label,
            notes=notes,
        )


# ---------- singleton ----------

_singleton_lock = threading.Lock()
_singleton: Optional[GeoService] = None


def get_geo_service() -> GeoService:
    global _singleton
    if _singleton is not None:
        return _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = GeoService()
        return _singleton
