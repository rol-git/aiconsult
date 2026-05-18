"""GeoAgent — отвечает на гео-ориентированные вопросы.

Источник правды: GeoService (OrbisMap карта паводков Тюм. области + Nominatim).

Поведение:
  - Если нет координат — просит у пользователя гео-разрешение или адрес в чате.
  - Если координаты вне Тюм. области — предупреждает и просит адрес внутри области.
  - Если в тексте сообщения есть адрес — геокодирует его (когда координат нет).
  - Использует «лёгкий agentic loop»: LLM решает, нужны ли доп. данные сверх
    гео-карточки (расширенный список ПВР по району, например), сервис достаёт
    их и LLM формулирует финальный ответ с маршрутными ссылками.
"""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from agents.base import AGENT_FOLLOWUPS, AgentType, AIResponse
from geo import GeoService, UserContext, UserLocation
from llm.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


_ADDRESS_HINT_RE = re.compile(
    r"\b("
    r"ул(?:ица|\.)|пр(?:оспект|\.)|пер(?:еулок|\.)|пл(?:ощадь|\.)?|"
    r"переулок|шоссе|микрорайон|мкр\.?|"
    r"г\.|город|село|поселок|поселёк|пос\.|деревня|дер\.|"
    r"д\.\s*\d+|корп\.|стр\."
    r")\b",
    re.IGNORECASE,
)


def _looks_like_address(text: str) -> bool:
    if not text:
        return False
    if _ADDRESS_HINT_RE.search(text):
        return True
    # «Тюмень, Республики 1» — без явных маркеров, но есть запятая и цифра
    if "," in text and any(ch.isdigit() for ch in text):
        return True
    return False


class GeoAgent:
    """Гео-агент с лёгкой agentic-логикой."""

    SYSTEM_PROMPT = (
        "Ты — гео-консультант сервиса помощи населению Тюменской области при ЧС. "
        "Ты работаешь на основе данных карты gis.72to.ru (Паводки 2026): "
        "пункты временного размещения (ПВР), зоны подтопления, перекрытия дорог, гидропосты.\n"
        "ВСЕГДА опирайся ТОЛЬКО на блок «Гео-контекст пользователя» и «Дополнительные данные», "
        "если они есть. Не выдумывай адреса, телефоны и ссылки.\n"
        "Если в гео-контексте указано «координаты не предоставлены» — мягко попроси разрешить "
        "геолокацию (кнопка в интерфейсе) или прислать адрес текстом.\n"
        "Если координаты вне Тюм. области — сообщи об этом и попроси прислать адрес внутри области.\n"
        "Если рекомендуешь ПВР — сразу прикладывай ссылки на маршрут в Яндекс.Картах и 2ГИС "
        "(они есть в гео-контексте, копируй их буквально). Не сокращай URL.\n"
        "Отвечай на русском в Markdown, кратко и по делу. Эмодзи можно использовать умеренно."
    )

    PLAN_SYSTEM = (
        "Ты — внутренний планировщик гео-агента. По вопросу пользователя и гео-карточке "
        "решаешь, нужны ли ДОПОЛНИТЕЛЬНЫЕ данные сверх карточки.\n"
        "Доступные инструменты:\n"
        "  - none: ничего не делать (карточка покрывает вопрос — выбирай это в БОЛЬШИНСТВЕ случаев)\n"
        "  - list_pvr_in_district: список ВСЕХ ПВР конкретного района/города. Выбирай ТОЛЬКО если "
        "пользователь явно просит «все ПВР в X», «список ПВР района X», «сколько ПВР в X». "
        "В обычном вопросе «где ближайший ПВР» — карточки уже хватает, выбирай none.\n"
        "  - geocode_and_check: геокодировать ТЕКСТОВЫЙ адрес из сообщения пользователя. "
        "Выбирай ТОЛЬКО если в сообщении пользователя есть НОВЫЙ текстовый адрес "
        "(улица/дом/город) И в гео-карточке стоит «координаты не предоставлены». "
        "ЗАПРЕЩЕНО передавать в address числовые координаты — это не адрес. "
        "Если в карточке уже есть координаты — почти всегда none.\n"
        "Верни СТРОГО валидный JSON: "
        '{"tool":"none|list_pvr_in_district|geocode_and_check","params":{...}}.'
    )

    _COORD_PAIR_RE = re.compile(r"^\s*-?\d+(?:[.,]\d+)?\s*[,;]\s*-?\d+(?:[.,]\d+)?\s*$")

    def __init__(self, geo_service: GeoService, client: OpenRouterClient) -> None:
        self.agent_type = AgentType.GEO
        self.geo = geo_service
        self.client = client

    def run(
        self,
        question: str,
        *,
        history: Optional[str] = None,
        user_context: Optional[UserContext] = None,
    ) -> AIResponse:
        user_context = user_context or UserContext()
        question_norm = (question or "").strip()

        # Если в самом сообщении встроен адрес, а координат нет — попробуем геокодировать.
        if (not user_context.location or not user_context.location.lat) and _looks_like_address(question_norm):
            try:
                geocoded = self.geo.geocode_address(question_norm)
            except Exception as exc:
                logger.warning("geocode by address failed: %s", exc)
                geocoded = None
            if geocoded:
                user_context.location = geocoded
                user_context.address_text = question_norm
                user_context.geo_card = self.geo.build_geo_card(geocoded)

        # Если карточки ещё нет, но координаты есть — построим
        if user_context.geo_card is None and user_context.location:
            user_context.geo_card = self.geo.build_geo_card(user_context.location)

        # Если совсем нет ни координат, ни адреса — спецветка
        if user_context.location is None:
            return self._ask_for_location(question_norm, history)

        # Если вне Тюм. области — спецветка
        if user_context.geo_card and not user_context.geo_card.in_tyumen:
            return self._outside_tyumen(question_norm, user_context, history)

        # Планировщик: решает, нужны ли доп. данные
        extra = self._plan_and_fetch(question_norm, user_context, history)

        return self._final_answer(question_norm, user_context, extra, history)

    # ---------- спецветки ----------

    def _ask_for_location(self, question: str, history: Optional[str]) -> AIResponse:
        answer = (
            "Чтобы подсказать ближайший ПВР, маршрут или зону риска, мне нужно знать ваше "
            "местоположение.\n\n"
            "Пожалуйста, либо **разрешите доступ к геолокации** в браузере (значок в адресной "
            "строке или баннер сверху), либо **напишите ваш адрес** прямо в сообщении — "
            "например: «Тюмень, ул. Республики, 1»."
        )
        return AIResponse(
            answer=answer,
            agent_types=[self.agent_type],
            sources=[],
            notes="need_location",
            suggested_questions=AGENT_FOLLOWUPS[self.agent_type],
        )

    def _outside_tyumen(
        self,
        question: str,
        user_context: UserContext,
        history: Optional[str],
    ) -> AIResponse:
        loc = user_context.location
        loc_str = f"{loc.lat:.4f}, {loc.lon:.4f}" if loc else "—"
        answer = (
            f"Ваше местоположение ({loc_str}) определилось **вне Тюменской области**. "
            "Этот сервис работает только по Тюм. области.\n\n"
            "Если вы сейчас в Тюм. области — напишите ваш адрес в сообщении, и я подскажу по нему. "
            "Если вы вне области, но у вас остались близкие в зоне ЧС — также напишите их адрес."
        )
        return AIResponse(
            answer=answer,
            agent_types=[self.agent_type],
            sources=[],
            notes="outside_region",
            suggested_questions=AGENT_FOLLOWUPS[self.agent_type],
        )

    # ---------- планировщик и финал ----------

    def _plan_and_fetch(
        self,
        question: str,
        user_context: UserContext,
        history: Optional[str],
    ) -> Optional[str]:
        """Один шаг tool-вызова. Возвращает блок текста «Дополнительные данные» или None."""
        if not user_context.geo_card:
            return None

        plan_user_msg = (
            f"Вопрос пользователя: {question}\n\n"
            f"Гео-карточка:\n{user_context.geo_card.to_prompt_block()[:2000]}\n\n"
            "Что нужно дополнительно? Верни JSON."
        )
        try:
            raw = self.client.complete(
                [
                    {"role": "system", "content": self.PLAN_SYSTEM},
                    {"role": "user", "content": plan_user_msg},
                ],
                temperature=0.0,
                max_tokens=200,
            )
            data = json.loads(self._strip_code_fence(raw))
            tool = (data.get("tool") or "none").strip().lower()
            params = data.get("params") or {}
        except Exception as exc:
            logger.debug("plan parse failed: %s — пропускаю tool-step", exc)
            return None

        if tool == "list_pvr_in_district":
            district = str(params.get("district") or "").strip()
            if not district:
                return None
            pvrs = self.geo.list_pvr_in_district(district)
            if not pvrs:
                return f"Дополнительные данные: ПВР в районе «{district}» не найдены."
            lines = [f"Дополнительные данные — ПВР в районе «{district}» ({len(pvrs)}):"]
            for p in pvrs[:20]:
                lines.append(f"  - {p.name} | {p.address} | тел. {p.phone} | вмест. {p.capacity or '?'}")
            return "\n".join(lines)

        if tool == "geocode_and_check":
            address = str(params.get("address") or "").strip()
            if not address:
                return None
            # Защита от ошибки планировщика: координаты как адрес — игнорируем
            if self._COORD_PAIR_RE.match(address):
                logger.info("planner попытался геокодировать координаты как адрес: %r — игнорирую", address)
                return None
            # Если координаты уже есть и совпадают с тем что у нас — нет смысла
            if user_context.location and not _looks_like_address(address):
                return None
            loc = self.geo.geocode_address(address)
            if not loc:
                return f"Дополнительные данные: не удалось определить координаты для «{address}»."
            new_card = self.geo.build_geo_card(loc)
            user_context.location = loc
            user_context.address_text = address
            user_context.geo_card = new_card
            return "Дополнительные данные: координаты были обновлены по адресу из сообщения. См. свежий гео-контекст."

        return None

    def _final_answer(
        self,
        question: str,
        user_context: UserContext,
        extra: Optional[str],
        history: Optional[str],
    ) -> AIResponse:
        history_block = f"Контекст беседы:\n{history.strip()}\n\n" if history else ""
        card_block = user_context.geo_card.to_prompt_block() if user_context.geo_card else ""

        user_msg = (
            f"{history_block}"
            f"{card_block}\n\n"
            f"{extra + chr(10) + chr(10) if extra else ''}"
            f"Вопрос пользователя: {question}\n\n"
            "Сформулируй полезный ответ. Если рекомендуешь ПВР — приводи имя, адрес, телефон, "
            "расстояние и обе маршрутные ссылки (Яндекс.Карты + 2ГИС) из гео-контекста буквально."
        )
        answer = self.client.complete(
            [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        return AIResponse(
            answer=answer.strip(),
            agent_types=[self.agent_type],
            sources=[],
            suggested_questions=AGENT_FOLLOWUPS[self.agent_type][:3],
        )

    # ---------- утилиты ----------

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        t = text.strip()
        if t.startswith("```"):
            # ```json ... ```
            t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
            t = re.sub(r"\s*```$", "", t)
        return t.strip()
