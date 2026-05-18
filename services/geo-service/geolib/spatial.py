"""Pure-spatial-операции через shapely (без БД, всё в памяти)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from shapely.geometry import Point, Polygon, MultiPolygon, shape
from shapely.geometry.base import BaseGeometry

EARTH_R_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние по большому кругу в км."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a))


@dataclass
class _SpatialFeature:
    """Лёгкая обёртка для shapely-фичей."""
    id: int
    geometry: BaseGeometry
    properties: dict
    centroid_lat: float
    centroid_lon: float


def feature_from_geojson(feat: dict) -> Optional[_SpatialFeature]:
    geom_raw = feat.get("geometry")
    if not geom_raw:
        return None
    try:
        geometry = shape(geom_raw)
    except Exception:
        return None
    c = geometry.centroid
    return _SpatialFeature(
        id=int(feat.get("id", 0)),
        geometry=geometry,
        properties=feat.get("properties") or {},
        centroid_lat=c.y,
        centroid_lon=c.x,
    )


def nearest_points_by_distance(
    user_lat: float,
    user_lon: float,
    features: Iterable[_SpatialFeature],
    k: int = 3,
    max_km: float = 500.0,
) -> List[Tuple[_SpatialFeature, float]]:
    """Top-K ближайших точечных фичей по haversine. max_km — отсечка."""
    scored: List[Tuple[_SpatialFeature, float]] = []
    for feat in features:
        d = haversine_km(user_lat, user_lon, feat.centroid_lat, feat.centroid_lon)
        if d <= max_km:
            scored.append((feat, d))
    scored.sort(key=lambda x: x[1])
    return scored[:k]


def point_in_any(lat: float, lon: float, features: Iterable[_SpatialFeature]) -> Optional[_SpatialFeature]:
    """Вернёт первую полигональную фичу, содержащую точку (lat, lon)."""
    pt = Point(lon, lat)  # shapely: x=lon, y=lat
    for feat in features:
        try:
            if feat.geometry.contains(pt) or feat.geometry.intersects(pt):
                return feat
        except Exception:
            continue
    return None


def nearest_polygon_km(
    lat: float,
    lon: float,
    features: Iterable[_SpatialFeature],
) -> Optional[Tuple[_SpatialFeature, float]]:
    """Ближайший полигон по дистанции до границы (приближение по центроиду + bbox)."""
    pt = Point(lon, lat)
    best: Optional[Tuple[_SpatialFeature, float]] = None
    for feat in features:
        try:
            if feat.geometry.contains(pt):
                return feat, 0.0
            # Расстояние до bbox в градусах -> грубо в км через haversine от ближайшей вершины
            minx, miny, maxx, maxy = feat.geometry.bounds
            # ближайшая точка по широте/долготе на границе bbox
            clamped_lat = max(miny, min(lat, maxy))
            clamped_lon = max(minx, min(lon, maxx))
            d = haversine_km(lat, lon, clamped_lat, clamped_lon)
        except Exception:
            continue
        if best is None or d < best[1]:
            best = (feat, d)
    return best
