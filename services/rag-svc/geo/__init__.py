"""Гео-модели — общий контракт между монолитом и geo-service.

Реальная бизнес-логика (запросы к паводок72, геокодинг, spatial) живёт в
services/geo-service. Здесь — только датаклассы, которые умеют
сериализоваться/десериализоваться в JSON.
"""

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

__all__ = [
    "FloodCheck",
    "GeoCard",
    "HydroPost",
    "MapLinks",
    "NearestPVR",
    "PVR",
    "RoadPoint",
    "UserContext",
    "UserLocation",
]
