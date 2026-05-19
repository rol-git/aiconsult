"""docs-ingestor: периодическая пересборка pgvector-индекса.

В текущем виде — минимальный daemon, который раз в INGEST_INTERVAL_HOURS
дёргает POST {RAG_SERVICE_URL}/rebuild и логирует результат. По мере
развития сюда переедут:
  * подтягивание свежих НПА из открытых источников;
  * LLM-классификация актуальности (релевантно/устарело);
  * семантический diff и точечное обновление чанков в pgvector.

Очередь и планировщик (RQ + RQ-scheduler) подключим, когда задач станет
больше одной — пока хватает простого цикла со сном.
"""

from __future__ import annotations

import logging
import os
import signal
import time

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("docs-ingestor")


RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-svc:5000").rstrip("/")
INGEST_INTERVAL_HOURS = float(os.getenv("INGEST_INTERVAL_HOURS", "24"))
INGEST_INTERVAL_S = int(INGEST_INTERVAL_HOURS * 3600)
INITIAL_DELAY_S = int(os.getenv("INGEST_INITIAL_DELAY_S", "60"))
REBUILD_TIMEOUT_S = float(os.getenv("INGEST_REBUILD_TIMEOUT_S", "600"))


_stop = False


def _on_signal(signum, _frame) -> None:
    global _stop
    logger.info("docs-ingestor: получен сигнал %s, останавливаюсь", signum)
    _stop = True


def trigger_rebuild() -> None:
    logger.info("Запуск пересборки индекса через %s/rebuild", RAG_SERVICE_URL)
    try:
        resp = httpx.post(f"{RAG_SERVICE_URL}/rebuild", timeout=REBUILD_TIMEOUT_S)
        if resp.status_code == 200:
            logger.info("Пересборка завершена успешно")
        else:
            logger.warning("rebuild ответил %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.exception("rebuild failed: %s", exc)


def _sleep_with_break(seconds: int) -> None:
    """time.sleep с быстрой реакцией на SIGTERM."""
    end = time.monotonic() + seconds
    while not _stop and time.monotonic() < end:
        time.sleep(min(5, end - time.monotonic()))


def main() -> None:
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    logger.info(
        "docs-ingestor стартовал: интервал=%sч, начальная задержка=%sс, rag=%s",
        INGEST_INTERVAL_HOURS,
        INITIAL_DELAY_S,
        RAG_SERVICE_URL,
    )

    _sleep_with_break(INITIAL_DELAY_S)
    while not _stop:
        trigger_rebuild()
        _sleep_with_break(INGEST_INTERVAL_S)

    logger.info("docs-ingestor завершил работу")


if __name__ == "__main__":
    main()
