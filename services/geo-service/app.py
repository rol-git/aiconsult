"""geo-service: HTTP-обёртка над GeoService (паводок72 + Nominatim).

Эндпоинты:
  GET  /health                — живой
  GET  /ready                 — готов отдавать данные (карта прогрелась)
  GET  /profile?lat&lon[&accuracy]
                              — гео-карточка (ПВР, флуд-риск, гидропост, заметки)
  GET  /geocode?q=...         — координаты по адресу (Nominatim)
  GET  /pvr?district=...      — все ПВР района по подстроке
"""

from __future__ import annotations

import logging
import os
import threading

from flask import Flask, jsonify, request
from flask_cors import CORS

from geolib import UserLocation, get_geo_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("geo-service")


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

_ready = threading.Event()


def _prewarm() -> None:
    try:
        get_geo_service().prewarm()
        logger.info("geo-service: ПВР-слой прогрет")
    except Exception as exc:
        logger.warning("geo-service prewarm failed: %s", exc)
    finally:
        _ready.set()


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "geo-service"}), 200


@app.get("/ready")
def ready():
    return jsonify({"ready": _ready.is_set()}), (200 if _ready.is_set() else 503)


@app.get("/profile")
def profile():
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "lat и lon обязательны"}), 400
    acc_raw = request.args.get("accuracy")
    try:
        acc = float(acc_raw) if acc_raw is not None else None
    except ValueError:
        acc = None

    location = UserLocation(lat=lat, lon=lon, accuracy_m=acc, source=request.args.get("source", "browser"))
    try:
        card = get_geo_service().build_geo_card(location)
    except Exception as exc:
        logger.exception("build_geo_card failed: %s", exc)
        return jsonify({"error": "geo backend unavailable"}), 503
    return jsonify({"profile": card.to_dict()})


@app.get("/geocode")
def geocode():
    text = (request.args.get("q") or "").strip()
    if not text:
        return jsonify({"error": "q обязателен"}), 400
    loc = get_geo_service().geocode_address(text)
    if not loc:
        return jsonify({"location": None}), 404
    return jsonify({"location": loc.to_dict()})


@app.get("/pvr")
def pvr_in_district():
    district = (request.args.get("district") or "").strip()
    if not district:
        return jsonify({"error": "district обязателен"}), 400
    items = get_geo_service().list_pvr_in_district(district)
    return jsonify({"items": [p.to_dict() for p in items]})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    threading.Thread(target=_prewarm, daemon=True, name="geo-prewarm").start()
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
