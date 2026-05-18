"""Yandex SpeechKit STT v3 client (gRPC bidirectional streaming)."""

import logging
from typing import Iterator, List

import grpc
from yandex.cloud.ai.stt.v3 import stt_pb2
from yandex.cloud.ai.stt.v3 import stt_service_pb2_grpc

logger = logging.getLogger(__name__)

STT_ENDPOINT = "stt.api.cloud.yandex.net:443"
CHUNK_SIZE = 4000


def _session_options(sample_rate_hz: int) -> stt_pb2.StreamingOptions:
    return stt_pb2.StreamingOptions(
        recognition_model=stt_pb2.RecognitionModelOptions(
            audio_format=stt_pb2.AudioFormatOptions(
                raw_audio=stt_pb2.RawAudio(
                    audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                    sample_rate_hertz=sample_rate_hz,
                    audio_channel_count=1,
                )
            ),
            text_normalization=stt_pb2.TextNormalizationOptions(
                text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
                profanity_filter=False,
                literature_text=False,
            ),
            language_restriction=stt_pb2.LanguageRestrictionOptions(
                restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                language_code=["ru-RU"],
            ),
            audio_processing_type=stt_pb2.RecognitionModelOptions.REAL_TIME,
        )
    )


def transcribe_pcm(
    pcm_bytes: bytes,
    api_key: str,
    folder_id: str,
    sample_rate_hz: int = 48000,
    timeout: float = 30.0,
) -> str:
    def request_iter() -> Iterator[stt_pb2.StreamingRequest]:
        yield stt_pb2.StreamingRequest(session_options=_session_options(sample_rate_hz))
        for i in range(0, len(pcm_bytes), CHUNK_SIZE):
            yield stt_pb2.StreamingRequest(
                chunk=stt_pb2.AudioChunk(data=pcm_bytes[i:i + CHUNK_SIZE])
            )

    channel = grpc.secure_channel(STT_ENDPOINT, grpc.ssl_channel_credentials())
    stub = stt_service_pb2_grpc.RecognizerStub(channel)
    metadata = (
        ("authorization", f"Api-Key {api_key}"),
        ("x-folder-id", folder_id),
    )

    finals: List[str] = []
    try:
        responses = stub.RecognizeStreaming(request_iter(), metadata=metadata, timeout=timeout)
        for response in responses:
            event_type = response.WhichOneof("Event")
            if event_type == "final":
                alts = response.final.alternatives
                if alts and alts[0].text:
                    finals.append(alts[0].text)
            elif event_type == "final_refinement":
                refined = response.final_refinement.normalized_text.alternatives
                if refined and refined[0].text:
                    if finals:
                        finals[-1] = refined[0].text
                    else:
                        finals.append(refined[0].text)
    finally:
        channel.close()

    return " ".join(finals).strip()
