"""Endpoint for voice transcription via Yandex SpeechKit STT v3."""

import logging
import os

import grpc
from flask import Blueprint, jsonify, request

from voice.audio_utils import to_lpcm
from voice.yandex_stt import transcribe_pcm

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 10 * 1024 * 1024
SAMPLE_RATE_HZ = 48000


def create_voice_blueprint() -> Blueprint:
    bp = Blueprint("voice", __name__, url_prefix="/api/voice")

    @bp.route("/transcribe", methods=["POST"])
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
            logger.error("Audio conversion failed: %s", exc)
            return jsonify({"error": "Не удалось обработать аудио"}), 400

        if not pcm_bytes:
            return jsonify({"error": "Аудио пустое после конвертации"}), 400

        try:
            text = transcribe_pcm(pcm_bytes, api_key, folder_id, sample_rate_hz=SAMPLE_RATE_HZ)
        except grpc.RpcError as exc:
            code = exc.code() if hasattr(exc, "code") else None
            logger.error("Yandex STT RPC error %s: %s", code, exc.details() if hasattr(exc, "details") else exc)
            if code == grpc.StatusCode.UNAUTHENTICATED:
                return jsonify({"error": "Неверный API-ключ Yandex"}), 401
            if code == grpc.StatusCode.PERMISSION_DENIED:
                return jsonify({"error": "Нет доступа к Yandex SpeechKit (роль/folder_id)"}), 403
            return jsonify({"error": "Yandex STT недоступен"}), 502
        except Exception:
            logger.exception("Yandex STT unexpected error")
            return jsonify({"error": "Ошибка распознавания"}), 500

        return jsonify({"text": text})

    return bp
