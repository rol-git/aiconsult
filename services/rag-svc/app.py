"""rag-svc: HTTP API над мультиагентной системой (RAG + OpenRouter + geo-svc).

Эндпоинты:
  GET  /health             — живой
  GET  /ready              — модель загружена, БД доступна
  POST /generate_answer    — основной вызов, ответ AIResponse JSON
  POST /rebuild            — пересоздать pgvector-индекс из docs/
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

from factory import get_factory
from geo import UserContext, UserLocation
from semantic_cache import SemanticCache


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("rag-svc")


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


_ready = threading.Event()
_cache: Optional[SemanticCache] = None


def _bootstrap() -> None:
    """Грузим модель и индекс в фоне, чтобы /health отвечал сразу."""
    global _cache
    try:
        factory = get_factory()
        cfg = factory.config()
        ai = factory.ai()  # init RAG + LLM + GeoClient
        # тёплый rag.retrieve один раз — заставит загрузить эмбеддер и retriever
        factory.rag().ensure_ready()
        _cache = SemanticCache(
            factory.redis(),
            ttl_s=cfg.semantic_cache_ttl_s,
            enabled=cfg.semantic_cache_enabled,
        )
        logger.info("rag-svc прогрет (модель + индекс + LLM)")
    except Exception as exc:
        logger.exception("bootstrap failed: %s", exc)
    finally:
        _ready.set()


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "rag-svc"}), 200


@app.get("/ready")
def ready():
    if _ready.is_set():
        return jsonify({"ready": True}), 200
    return jsonify({"ready": False}), 503


def _parse_user_context(payload: Optional[Dict[str, Any]]) -> UserContext:
    if not payload:
        return UserContext()
    loc_raw = payload.get("location") if isinstance(payload, dict) else None
    location: Optional[UserLocation] = None
    if isinstance(loc_raw, dict):
        try:
            location = UserLocation.from_dict(loc_raw)
        except Exception as exc:
            logger.warning("bad location payload: %s", exc)
    return UserContext(location=location, address_text=payload.get("addressText"))


@app.post("/generate_answer")
def generate_answer():
    if not _ready.is_set():
        return jsonify({"error": "rag-svc warming up"}), 503

    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question обязателен"}), 400
    if len(question) > 5000:
        return jsonify({"error": "question слишком длинный (макс. 5000)"}), 400

    history = data.get("history") or None
    user_ctx = _parse_user_context(data.get("userContext"))

    # cache key игнорирует userContext: если в нём только координаты, ответы будут разными,
    # но базовая логика покрывает FAQ-короткие замыкания на тексте.
    cached = _cache.get(question, history) if _cache else None
    if cached is not None:
        cached["cached"] = True
        return jsonify(cached), 200

    try:
        ai_resp = get_factory().ai().generate_answer(question, context=history, user_context=user_ctx)
    except Exception as exc:
        logger.exception("generate_answer failed: %s", exc)
        return jsonify({"error": f"rag-svc error: {exc}"}), 500

    payload = ai_resp.to_dict()
    if _cache is not None and not user_ctx.location:
        # геозависимые ответы НЕ кэшируем — иначе будем выдавать чужие ПВР
        _cache.set(question, history, payload)
    return jsonify(payload), 200


@app.post("/rebuild")
def rebuild():
    """Перестроить pgvector-индекс из docs/. Долгая операция (минуты)."""
    try:
        get_factory().rag().rebuild()
    except Exception as exc:
        logger.exception("rebuild failed: %s", exc)
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    threading.Thread(target=_bootstrap, daemon=True, name="rag-bootstrap").start()
    port = get_factory().config().port
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
