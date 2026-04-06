"""AI-powered message parser using Gemini via OpenAI-compatible API."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from openai import OpenAI

from bot.config import GEMINI_API_KEY, logger

_client: OpenAI | None = None

SYSTEM_PROMPT = """\
Ты — парсер сообщений для Telegram-бота списка покупок. Твоя задача — разобрать сообщение пользователя и вернуть JSON.

Доступные категории товаров:
Фрукты, Овощи, Молочка, Бакалея, Мясо, Рыба, Заморозка, Напитки, Хлеб, Сладкое, Прочее

Возможные intent:
- "add" — пользователь хочет добавить товары в список
- "remove" — пользователь хочет удалить конкретные товары из списка
- "remove_category" — пользователь хочет удалить все товары определённой категории
- "show" — пользователь хочет посмотреть список
- "clear" — пользователь хочет полностью очистить список
- "undo" — пользователь хочет отменить последнее удаление

Формат ответа — строго JSON, без markdown:

Для add:
{"intent": "add", "items": [{"name": "сыр в нарезке", "category": "Молочка"}, ...]}

Для remove:
{"intent": "remove", "items": [{"name": "молоко"}, {"name": "хлеб"}]}

Для remove_category:
{"intent": "remove_category", "category": "Прочее"}

Для show:
{"intent": "show"}

Для clear:
{"intent": "clear"}

Для undo:
{"intent": "undo"}

Правила:
- Товар записывай так, как его назвал пользователь, но без слов-команд (купи, добавь, удали, и т.д.)
- Составные названия вроде "сыр в нарезке", "филе куриное", "масло оливковое" — это ОДИН товар, не разбивай
- Для add обязательно укажи category из списка выше
- "удали всю категорию X" или "убери категорию X" — это remove_category
- "удали молоко" — это remove (конкретный товар)
- "удали список" / "очисти список" — это clear
- Если не уверен в категории, ставь "Прочее"
- Не добавляй от себя товары, которых нет в сообщении
- "отмени удаление", "верни обратно", "отмена", "отменить" — это undo
"""


@dataclass
class ParseResult:
    intent: str  # add | remove | remove_category | show | clear
    items: list[dict] = field(default_factory=list)  # [{name, category?}]
    category: str = ""  # for remove_category


def _get_client() -> OpenAI | None:
    global _client
    if _client is not None:
        return _client
    if not GEMINI_API_KEY:
        return None
    _client = OpenAI(
        api_key=GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    return _client


def parse_message(text: str) -> ParseResult | None:
    """Send user text to Gemini and return structured ParseResult, or None on failure."""
    client = _get_client()
    if client is None:
        return None

    try:
        resp = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=500,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        logger.info("AI raw response: %s", raw)

        # Strip possible markdown fences
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        data = json.loads(raw)
        return _parse_json(data)

    except Exception:
        logger.exception("AI parser failed")
        return None


def _parse_json(data: dict) -> ParseResult:
    intent = data.get("intent", "add")
    if intent not in ("add", "remove", "remove_category", "show", "clear", "undo"):
        intent = "add"

    items: list[dict] = []
    for item in data.get("items", []):
        if isinstance(item, dict) and item.get("name"):
            items.append(item)
        elif isinstance(item, str) and item.strip():
            items.append({"name": item.strip()})

    category = data.get("category", "")

    return ParseResult(intent=intent, items=items, category=category)
