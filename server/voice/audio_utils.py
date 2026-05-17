"""Audio conversion helpers: arbitrary container -> raw LPCM 16-bit mono."""

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def to_lpcm(input_bytes: bytes, sample_rate_hz: int = 48000) -> bytes:
    proc = subprocess.run(
        [
            FFMPEG,
            "-hide_banner", "-loglevel", "error",
            "-i", "pipe:0",
            "-ac", "1",
            "-ar", str(sample_rate_hz),
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "pipe:1",
        ],
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(f"ffmpeg failed: {err or 'unknown error'}")
    return proc.stdout
