"""stt-service: HTTP-обёртка над Yandex SpeechKit STT v3.

POST /transcribe (multipart/form-data, поле audio) → {"text": "..."}.
"""

from __future__ import annotations

import logging
import os

import grpc
from flask import Flask, jsonify, request
from flask_cors import CORS

from audio_utils import to_lpcm
from yandex_stt import transcribe_pcm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("stt-service")


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


MAX_AUDIO_BYTES = 10 * 1024 * 1024
SAMPLE_RATE_HZ = 48000


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "stt-service"}), 200


@app.post("/transcribe")
def transcribe():
    api_key = os.getenv("YC_API_KEY")
    folder_id = os.getenv("YC_FOLDER_ID")
    if not api_key or not folder_id:
        return jsonify({"error": "Yandex SpeechKit не сконфигурирован (YC_API_KEY/YC_FOLDER_ID)"}), 503

    if "audio" not in request.files:
        return jsonify({"error": "Файл audio не передан"}), 400
    audio_bytes = request.files["audio"].read()
    if not audio_bytes:
        return jsonify({"error": "Пустой аудиофайл"}), 400
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        return jsonify({"error": "Аудио слишком большое"}), 413

    try:
        pcm_bytes = to_lpcm(audio_bytes, sample_rate_hz=SAMPLE_RATE_HZ)
    except RuntimeError as exc:
        logger.error("audio conversion failed: %s", exc)
        return jsonify({"error": "Не удалось обработать аудио"}), 400
    if not pcm_bytes:
        return jsonify({"error": "Аудио пустое после конвертации"}), 400

    try:
        text = transcribe_pcm(pcm_bytes, api_key, folder_id, sample_rate_hz=SAMPLE_RATE_HZ)
    except grpc.RpcError as exc:
        code = exc.code() if hasattr(exc, "code") else None
        logger.error("Yandex STT RPC error %s", code)
        if code == grpc.StatusCode.UNAUTHENTICATED:
            return jsonify({"error": "Неверный API-ключ Yandex"}), 401
        if code == grpc.StatusCode.PERMISSION_DENIED:
            return jsonify({"error": "Нет доступа к Yandex SpeechKit (роль/folder_id)"}), 403
        return jsonify({"error": "Yandex STT недоступен"}), 502
    except Exception:
        logger.exception("Yandex STT unexpected error")
        return jsonify({"error": "Ошибка распознавания"}), 500

    return jsonify({"text": text})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
