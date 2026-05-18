"""Генерация ссылок на маршруты в Яндекс.Картах и 2ГИС."""

from __future__ import annotations

from typing import Optional


def yandex_route_url(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    mode: str = "auto",
) -> str:
    """Яндекс.Карты: rtext=lat,lon~lat,lon&rtt=auto|mt|pd|bicycle."""
    rtt = {"auto": "auto", "transit": "mt", "walk": "pd", "bike": "bc"}.get(mode, "auto")
    return (
        f"https://yandex.ru/maps/?rtext={from_lat:.6f},{from_lon:.6f}~"
        f"{to_lat:.6f},{to_lon:.6f}&rtt={rtt}"
    )


def dgis_route_url(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    mode: str = "auto",
) -> str:
    """2ГИС: lon,lat (X,Y!). Path: /routeSearch/rsType/<mode>/from/.../to/..."""
    rs_type = {"auto": "car", "transit": "bus", "walk": "pedestrian", "bike": "bicycle"}.get(mode, "car")
    return (
        f"https://2gis.ru/routeSearch/rsType/{rs_type}"
        f"/from/{from_lon:.6f},{from_lat:.6f}"
        f"/to/{to_lon:.6f},{to_lat:.6f}"
    )


def dgis_point_url(lat: float, lon: float) -> str:
    """Карточка точки в 2ГИС (без маршрута, если откуда — неизвестно)."""
    return f"https://2gis.ru/geo/{lon:.6f},{lat:.6f}"


def yandex_point_url(lat: float, lon: float) -> str:
    return f"https://yandex.ru/maps/?pt={lon:.6f},{lat:.6f}&z=16&l=map"


def build_route_pair(
    from_lat: Optional[float],
    from_lon: Optional[float],
    to_lat: float,
    to_lon: float,
    mode: str = "auto",
) -> dict:
    """Возвращает {yandex, dgis} ссылки. Если from_* нет — даём ссылку на точку."""
    if from_lat is not None and from_lon is not None:
        return {
            "yandex": yandex_route_url(from_lat, from_lon, to_lat, to_lon, mode),
            "dgis": dgis_route_url(from_lat, from_lon, to_lat, to_lon, mode),
        }
    return {
        "yandex": yandex_point_url(to_lat, to_lon),
        "dgis": dgis_point_url(to_lat, to_lon),
    }
