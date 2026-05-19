"""Dataclasses для geo-слоя. Используются и для сериализации, и для парсинга
ответов geo-service (HTTP)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class UserLocation:
    lat: float
    lon: float
    accuracy_m: Optional[float] = None
    source: str = "browser"  # browser | geocoded | manual

    def to_dict(self) -> dict:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "accuracyM": self.accuracy_m,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserLocation":
        return cls(
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            accuracy_m=_coerce_float(data.get("accuracyM") or data.get("accuracy_m")),
            source=str(data.get("source") or "browser"),
        )


@dataclass
class MapLinks:
    yandex: str
    dgis: str
    dgis_object: Optional[str] = None

    def to_dict(self) -> dict:
        out = {"yandex": self.yandex, "dgis": self.dgis}
        if self.dgis_object:
            out["dgisObject"] = self.dgis_object
        return out

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MapLinks":
        return cls(
            yandex=str(data.get("yandex") or ""),
            dgis=str(data.get("dgis") or ""),
            dgis_object=data.get("dgisObject"),
        )


@dataclass
class PVR:
    pvr_id: int
    name: str
    address: str
    district: str
    settlement: str
    phone: str
    capacity: Optional[str]
    lat: float
    lon: float
    dgis_route_link: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.pvr_id,
            "name": self.name,
            "address": self.address,
            "district": self.district,
            "settlement": self.settlement,
            "phone": self.phone,
            "capacity": self.capacity,
            "lat": self.lat,
            "lon": self.lon,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PVR":
        return cls(
            pvr_id=int(data.get("id") or 0),
            name=str(data.get("name") or ""),
            address=str(data.get("address") or ""),
            district=str(data.get("district") or ""),
            settlement=str(data.get("settlement") or ""),
            phone=str(data.get("phone") or ""),
            capacity=data.get("capacity"),
            lat=float(data.get("lat") or 0.0),
            lon=float(data.get("lon") or 0.0),
        )


@dataclass
class NearestPVR:
    pvr: PVR
    distance_km: float
    links: MapLinks

    def to_dict(self) -> dict:
        return {
            **self.pvr.to_dict(),
            "distanceKm": round(self.distance_km, 2),
            "links": self.links.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NearestPVR":
        return cls(
            pvr=PVR.from_dict(data),
            distance_km=float(data.get("distanceKm") or 0.0),
            links=MapLinks.from_dict(data.get("links") or {}),
        )


@dataclass
class HydroPost:
    post_id: int
    lat: float
    lon: float
    properties: dict = field(default_factory=dict)


@dataclass
class RoadPoint:
    point_id: int
    kind: str  # "blocked" | "open"
    lat: float
    lon: float
    properties: dict = field(default_factory=dict)


@dataclass
class FloodCheck:
    in_max_zone: bool
    in_clean_zone: bool
    nearest_zone_km: Optional[float]
    nearest_zone_district: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FloodCheck":
        return cls(
            in_max_zone=bool(data.get("inMaxZone")),
            in_clean_zone=bool(data.get("inCleanZone")),
            nearest_zone_km=_coerce_float(data.get("nearestZoneKm")),
            nearest_zone_district=data.get("nearestZoneDistrict"),
        )


@dataclass
class GeoCard:
    """Компактная гео-карточка, подмешиваемая в системный промпт всех агентов."""
    location: Optional[UserLocation]
    in_tyumen: bool
    nearest_pvrs: List[NearestPVR]
    flood: Optional[FloodCheck]
    blocked_roads_nearby: int
    nearest_hydropost_km: Optional[float]
    address_label: Optional[str] = None  # reverse-геокод адрес (если удалось)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "location": self.location.to_dict() if self.location else None,
            "inTyumen": self.in_tyumen,
            "addressLabel": self.address_label,
            "nearestPvrs": [p.to_dict() for p in self.nearest_pvrs],
            "flood": {
                "inMaxZone": self.flood.in_max_zone if self.flood else False,
                "inCleanZone": self.flood.in_clean_zone if self.flood else False,
                "nearestZoneKm": self.flood.nearest_zone_km if self.flood else None,
                "nearestZoneDistrict": self.flood.nearest_zone_district if self.flood else None,
            } if self.flood else None,
            "blockedRoadsNearby": self.blocked_roads_nearby,
            "nearestHydropostKm": self.nearest_hydropost_km,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeoCard":
        loc_raw = data.get("location")
        flood_raw = data.get("flood")
        return cls(
            location=UserLocation.from_dict(loc_raw) if loc_raw else None,
            in_tyumen=bool(data.get("inTyumen")),
            nearest_pvrs=[NearestPVR.from_dict(item) for item in (data.get("nearestPvrs") or [])],
            flood=FloodCheck.from_dict(flood_raw) if flood_raw else None,
            blocked_roads_nearby=int(data.get("blockedRoadsNearby") or 0),
            nearest_hydropost_km=_coerce_float(data.get("nearestHydropostKm")),
            address_label=data.get("addressLabel"),
            notes=list(data.get("notes") or []),
        )

    def to_prompt_block(self) -> str:
        """Текстовое представление для системного промпта LLM."""
        if not self.location:
            return "Гео-контекст пользователя: координаты не предоставлены."

        coord_line = (
            f"Координаты пользователя: {self.location.lat:.5f}, {self.location.lon:.5f}"
            + (f" (точность ~{int(self.location.accuracy_m)} м)" if self.location.accuracy_m else "")
        )
        if self.address_label:
            coord_line += f"\nЧитаемый адрес: {self.address_label}"
        lines = [coord_line]
        if self.in_tyumen:
            lines.append("В Тюменской области: ДА")
        else:
            lines.append("В Тюменской области: НЕТ — сервис предназначен только для Тюм. области.")

        if self.flood:
            f_lines = []
            if self.flood.in_max_zone:
                f_lines.append("ВНУТРИ зоны максимального подтопления")
            if self.flood.in_clean_zone:
                f_lines.append("ВНУТРИ зоны активного («чистого») затопления")
            if not (self.flood.in_max_zone or self.flood.in_clean_zone):
                f_lines.append("вне известных зон подтопления")
            if self.flood.nearest_zone_km is not None:
                f_lines.append(
                    f"ближайший очаг подтопления ~{self.flood.nearest_zone_km:.1f} км"
                    + (f" ({self.flood.nearest_zone_district})" if self.flood.nearest_zone_district else "")
                )
            lines.append("Подтопления: " + "; ".join(f_lines) + ".")

        if self.nearest_pvrs:
            pvr_lines = ["Ближайшие ПВР:"]
            for i, n in enumerate(self.nearest_pvrs[:3], 1):
                pvr_lines.append(
                    f"  {i}. «{n.pvr.name}» — {n.pvr.address}, тел. {n.pvr.phone}, "
                    f"~{n.distance_km:.1f} км. Маршруты: Яндекс {n.links.yandex} | 2ГИС {n.links.dgis}"
                )
            lines.append("\n".join(pvr_lines))

        if self.blocked_roads_nearby:
            lines.append(f"Перекрытий дорог в радиусе 10 км: {self.blocked_roads_nearby}.")

        if self.nearest_hydropost_km is not None:
            lines.append(f"Ближайший гидропост ~{self.nearest_hydropost_km:.1f} км.")

        if self.notes:
            lines.append("Заметки: " + "; ".join(self.notes))

        return "Гео-контекст пользователя:\n" + "\n".join(lines)


@dataclass
class UserContext:
    """Контекст, передаваемый агентам — гео + историю + что угодно ещё."""
    location: Optional[UserLocation] = None
    address_text: Optional[str] = None  # если юзер написал адрес в чате
    geo_card: Optional[GeoCard] = None
    history: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "location": self.location.to_dict() if self.location else None,
            "addressText": self.address_text,
            "geoCard": self.geo_card.to_dict() if self.geo_card else None,
        }
