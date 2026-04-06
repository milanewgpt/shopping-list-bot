"""Telegram bot handlers."""

from __future__ import annotations

from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot import ai_parser, db, speech
from bot.categories import CATEGORY_ORDER, categorize
from bot.config import logger
from bot.parsing import detect_intent, extract_items, extract_items_to_remove, normalize

# Per-user undo buffer: user_id -> list of (raw_text, normalized, category)
_undo_buffer: dict[int, list[tuple[str, str, str]]] = {}


def _save_undo(user_id: int, items: list[tuple[str, str, str]]) -> None:
    if items:
        _undo_buffer[user_id] = items


def _pop_undo(user_id: int) -> list[tuple[str, str, str]]:
    return _undo_buffer.pop(user_id, [])


# ── /start, /help ────────────────────────────────────────────────────────────

HELP_TEXT = (
    "Я помогу вести список покупок.\n\n"
    "Просто напишите или надиктуйте товары:\n"
    "  молоко, хлеб, яблоки\n"
    "  купи сыр в нарезке и масло оливковое\n\n"
    "Удалить позиции:\n"
    "  удали молоко и хлеб\n"
    "  удали всю категорию Прочее\n\n"
    "Отменить последнее удаление:\n"
    "  отмени удаление\n\n"
    "Команды:\n"
    "  /list — показать список покупок\n"
    "  /clear — очистить список\n"
    "  /undo — отменить последнее удаление\n"
    "  /help — эта справка\n\n"
    "Также понимаю фразы:\n"
    '  "покажи список", "что купить"\n'
    '  "очисти список", "обнули список покупок"'
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Привет! {HELP_TEXT}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


# ── /list ─────────────────────────────────────────────────────────────────────

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_list(update)


async def _show_list(update: Update) -> None:
    user_id = update.effective_user.id
    items = db.get_items_by_category(user_id)
    if not items:
        await update.message.reply_text("Список покупок пуст.")
        return

    lines = ["Список покупок:\n"]
    for cat in CATEGORY_ORDER:
        cat_items = items.get(cat)
        if cat_items:
            lines.append(f"*{cat}:*")
            for name in cat_items:
                lines.append(f"  \\- {_escape_md(name)}")
            lines.append("")

    await update.message.reply_text(
        "\n".join(lines), parse_mode="MarkdownV2"
    )


def _escape_md(text: str) -> str:
    special = r"_*[]()~`>#+-=|{}.!"
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text


# ── /clear ────────────────────────────────────────────────────────────────────

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _clear_list(update)


async def _clear_list(update: Update) -> None:
    user_id = update.effective_user.id
    deleted = db.clear_items(user_id)
    if deleted:
        _save_undo(user_id, deleted)
        await update.message.reply_text(
            f"Список покупок очищен ({_plural(len(deleted), 'позиция', 'позиции', 'позиций')}).\n"
            "Чтобы отменить: /undo"
        )
    else:
        await update.message.reply_text("Список покупок и так пуст.")


# ── /undo ─────────────────────────────────────────────────────────────────────

async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _undo(update)


async def _undo(update: Update, transcription: str | None = None) -> None:
    user_id = update.effective_user.id
    items = _pop_undo(user_id)

    parts: list[str] = []
    if transcription:
        parts.append(f'Распознала: "{transcription}"\n')

    if not items:
        parts.append("Нечего отменять.")
        await update.message.reply_text("\n".join(parts))
        return

    try:
        db.restore_items(user_id, items)
    except Exception:
        logger.exception("Failed to restore items")
        parts.append("Не удалось восстановить. Попробуйте добавить заново.")
        await update.message.reply_text("\n".join(parts))
        return

    parts.append(f"Восстановила {_plural(len(items), 'позицию', 'позиции', 'позиций')}:")
    for raw, _norm, _cat in items:
        parts.append(f"  - {raw}")
    await update.message.reply_text("\n".join(parts))


# ── Unified message processing ───────────────────────────────────────────────

async def _process_message(
    update: Update, text: str, transcription: str | None
) -> None:
    result = ai_parser.parse_message(text)

    if result is not None:
        logger.info("AI intent=%s items=%s cat=%s", result.intent, result.items, result.category)
        await _handle_ai_result(update, result, transcription)
    else:
        logger.info("AI parser unavailable, using simple parser")
        await _handle_simple(update, text, transcription)


async def _handle_ai_result(
    update: Update,
    result: ai_parser.ParseResult,
    transcription: str | None,
) -> None:
    if result.intent == "show":
        if transcription:
            await update.message.reply_text(f'Распознала: "{transcription}"')
        await _show_list(update)

    elif result.intent == "clear":
        if transcription:
            await update.message.reply_text(f'Распознала: "{transcription}"')
        await _clear_list(update)

    elif result.intent == "undo":
        await _undo(update, transcription)

    elif result.intent == "remove_category":
        await _remove_category(update, result.category, transcription)

    elif result.intent == "remove":
        raw_items = [item["name"] for item in result.items if item.get("name")]
        if raw_items:
            await _remove_items(update, raw_items, transcription)
        else:
            msg = f'Распознала: "{transcription}"\n\n' if transcription else ""
            await update.message.reply_text(msg + "Не поняла, что удалить.")

    else:  # add
        if result.items:
            await _add_items_ai(update, result.items, transcription)
        else:
            msg = f'Распознала: "{transcription}"\n\n' if transcription else ""
            await update.message.reply_text(msg + "Не смогла разобрать товары. Попробуйте ещё раз.")


async def _handle_simple(
    update: Update, text: str, transcription: str | None
) -> None:
    intent = detect_intent(text)

    if intent == "show":
        if transcription:
            await update.message.reply_text(f'Распознала: "{transcription}"')
        await _show_list(update)
    elif intent == "clear":
        if transcription:
            await update.message.reply_text(f'Распознала: "{transcription}"')
        await _clear_list(update)
    elif intent == "undo":
        await _undo(update, transcription)
    elif intent == "remove":
        raw_items = extract_items_to_remove(text)
        if raw_items:
            await _remove_items(update, raw_items, transcription)
        else:
            msg = f'Распознала: "{transcription}"\n\n' if transcription else ""
            await update.message.reply_text(msg + "Не поняла, что удалить.")
    else:
        raw_items = extract_items(text)
        if raw_items:
            await _add_items(update, raw_items, transcription)
        else:
            msg = f'Распознала: "{transcription}"\n\n' if transcription else ""
            await update.message.reply_text(msg + "Не смогла разобрать товары. Попробуйте ещё раз.")


# ── Text messages ─────────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text:
        return
    await _process_message(update, text, transcription=None)


# ── Voice messages ────────────────────────────────────────────────────────────

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice = update.message.voice
    if not voice:
        return

    path: Path | None = None
    try:
        path = await speech.download_voice(voice, context.bot)
        text = await speech.transcribe_voice(path)
    except Exception:
        logger.exception("Voice processing failed")
        await update.message.reply_text(
            "Не удалось распознать голосовое сообщение. Попробуйте ещё раз."
        )
        return
    finally:
        if path and path.exists():
            path.unlink(missing_ok=True)

    if not text:
        await update.message.reply_text(
            "Не удалось распознать голосовое сообщение. Попробуйте ещё раз."
        )
        return

    await _process_message(update, text, transcription=text)


# ── Remove category ──────────────────────────────────────────────────────────

async def _remove_category(
    update: Update, category: str, transcription: str | None
) -> None:
    user_id = update.effective_user.id

    matched = _match_category(category)
    if not matched:
        msg = f'Распознала: "{transcription}"\n\n' if transcription else ""
        await update.message.reply_text(
            msg + f'Не нашла категорию "{category}". '
            f"Доступные: {', '.join(CATEGORY_ORDER)}"
        )
        return

    deleted = db.remove_by_category(user_id, matched)
    parts: list[str] = []
    if transcription:
        parts.append(f'Распознала: "{transcription}"\n')
    if deleted:
        _save_undo(user_id, deleted)
        parts.append(
            f"Удалила категорию «{matched}» ({_plural(len(deleted), 'позиция', 'позиции', 'позиций')}).\n"
            "Чтобы отменить: /undo"
        )
    else:
        parts.append(f"Категория «{matched}» и так пуста.")
    await update.message.reply_text("\n".join(parts))


def _match_category(name: str) -> str | None:
    low = name.lower().strip()
    for cat in CATEGORY_ORDER:
        if cat.lower() == low:
            return cat
    for cat in CATEGORY_ORDER:
        if low in cat.lower() or cat.lower() in low:
            return cat
    return None


# ── Remove specific items ─────────────────────────────────────────────────────

async def _remove_items(
    update: Update,
    raw_items: list[str],
    transcription: str | None,
) -> None:
    user_id = update.effective_user.id
    existing = db.get_existing_normalized(user_id)

    all_deleted: list[tuple[str, str, str]] = []
    removed_display: list[str] = []
    not_found: list[str] = []

    for raw in raw_items:
        norm = normalize(raw)
        if not norm:
            continue
        if norm in existing:
            try:
                deleted_rows = db.remove_items(user_id, [norm])
                all_deleted.extend(deleted_rows)
            except Exception:
                logger.exception("DB error removing item %s", raw)
                continue
            existing.discard(norm)
            removed_display.append(raw)
        else:
            not_found.append(raw)

    if all_deleted:
        _save_undo(user_id, all_deleted)

    parts: list[str] = []
    if transcription:
        parts.append(f'Распознала: "{transcription}"\n')
    if removed_display:
        parts.append(
            f"Удалила {_plural(len(removed_display), 'позицию', 'позиции', 'позиций')}:"
        )
        for name in removed_display:
            parts.append(f"  - {name}")
        parts.append("\nЧтобы отменить: /undo")
    if not_found:
        if removed_display:
            parts.append("")
        parts.append("Не нашла в списке:")
        for name in not_found:
            parts.append(f"  - {name}")
    if not removed_display and not not_found:
        parts.append("Не поняла, что удалить.")
    await update.message.reply_text("\n".join(parts))


# ── Add items (AI-parsed with categories) ─────────────────────────────────────

async def _add_items_ai(
    update: Update,
    ai_items: list[dict],
    transcription: str | None,
) -> None:
    user_id = update.effective_user.id
    existing = db.get_existing_normalized(user_id)

    added: list[tuple[str, str]] = []
    duplicates: list[str] = []

    for item in ai_items:
        raw = item.get("name", "").strip()
        if not raw:
            continue
        norm = normalize(raw)
        if not norm:
            continue
        if norm in existing:
            duplicates.append(raw)
            continue
        cat = item.get("category", "") or categorize(norm)
        matched_cat = _match_category(cat) if cat else None
        cat = matched_cat or categorize(norm)
        try:
            db.add_item(user_id, raw, norm, cat)
        except Exception:
            logger.exception("DB error adding item %s", raw)
            continue
        existing.add(norm)
        added.append((raw, cat))

    parts = _build_add_parts(added, duplicates, transcription)
    await update.message.reply_text("\n".join(parts))


# ── Add items (simple parser fallback) ────────────────────────────────────────

async def _add_items(
    update: Update,
    raw_items: list[str],
    transcription: str | None,
) -> None:
    user_id = update.effective_user.id
    existing = db.get_existing_normalized(user_id)

    added: list[tuple[str, str]] = []
    duplicates: list[str] = []

    for raw in raw_items:
        norm = normalize(raw)
        if not norm:
            continue
        if norm in existing:
            duplicates.append(raw)
            continue
        cat = categorize(norm)
        try:
            db.add_item(user_id, raw, norm, cat)
        except Exception:
            logger.exception("DB error adding item %s", raw)
            continue
        existing.add(norm)
        added.append((raw, cat))

    parts = _build_add_parts(added, duplicates, transcription)
    await update.message.reply_text("\n".join(parts))


def _build_add_parts(
    added: list[tuple[str, str]],
    duplicates: list[str],
    transcription: str | None,
) -> list[str]:
    parts: list[str] = []
    if transcription:
        parts.append(f'Распознала: "{transcription}"\n')
    if added:
        parts.append(f"Добавила {_plural(len(added), 'позицию', 'позиции', 'позиций')}.\n")
        by_cat: dict[str, list[str]] = {}
        for raw, cat in added:
            by_cat.setdefault(cat, []).append(raw)
        for cat in CATEGORY_ORDER:
            if cat in by_cat:
                parts.append(f"{cat}:")
                for name in by_cat[cat]:
                    parts.append(f"  - {name}")
    if duplicates:
        if added:
            parts.append("")
        parts.append("Уже были в списке:")
        for d in duplicates:
            parts.append(f"  - {d}")
    if not added and not duplicates:
        parts.append("Не удалось добавить товары.")
    return parts


def _plural(n: int, form1: str, form2: str, form5: str) -> str:
    n_abs = abs(n) % 100
    n1 = n_abs % 10
    if 11 <= n_abs <= 19:
        return f"{n} {form5}"
    if n1 == 1:
        return f"{n} {form1}"
    if 2 <= n1 <= 4:
        return f"{n} {form2}"
    return f"{n} {form5}"
