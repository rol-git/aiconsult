"""HTTP-эндпоинты для гео-данных: предзагрузка карточки, геокод адреса, ПВР списком."""

from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from geo import UserLocation, get_geo_service

logger = logging.getLogger(__name__)


def create_geo_blueprint() -> Blueprint:
    bp = Blueprint("geo", __name__, url_prefix="/api/geo")

    @bp.route("/profile", methods=["GET"])
    def profile():
        try:
            lat = float(request.args.get("lat"))
            lon = float(request.args.get("lon"))
        except (TypeError, ValueError):
            return jsonify({"error": "lat и lon обязательны"}), 400
        acc = request.args.get("accuracy")
        try:
            acc_f = float(acc) if acc is not None else None
        except ValueError:
            acc_f = None

        location = UserLocation(lat=lat, lon=lon, accuracy_m=acc_f, source="browser")
        geo = get_geo_service()
        try:
            card = geo.build_geo_card(location)
        except Exception as exc:
            logger.exception("Не удалось собрать гео-карточку: %s", exc)
            return jsonify({"error": "Карта временно недоступна"}), 503

        return jsonify({"profile": card.to_dict()})

    @bp.route("/geocode", methods=["GET"])
    def geocode():
        text = (request.args.get("q") or "").strip()
        if not text:
            return jsonify({"error": "q обязателен"}), 400
        geo = get_geo_service()
        loc = geo.geocode_address(text)
        if not loc:
            return jsonify({"location": None}), 404
        return jsonify({"location": loc.to_dict()})

    @bp.route("/pvr", methods=["GET"])
    def pvr_in_district():
        district = (request.args.get("district") or "").strip()
        if not district:
            return jsonify({"error": "district обязателен"}), 400
        geo = get_geo_service()
        items = geo.list_pvr_in_district(district)
        return jsonify({"items": [p.to_dict() for p in items]})

    return bp
