"""Extract and normalize product names from user text."""

from __future__ import annotations

import re

# Words to strip from the beginning/end of the input phrase
_STOP_WORDS: set[str] = {
    "добавь", "добавить", "купи", "купить", "нужно", "нужна", "нужны",
    "надо", "возьми", "взять", "запиши", "записать", "ещё", "еще",
    "пожалуйста", "плиз", "плз", "пож",
    "в", "на", "из", "список", "покупки", "покупок",
    "мне", "нам", "нужен",
}

# Normalisation dictionary: variant -> canonical form
_NORM_MAP: dict[str, str] = {
    "помидор": "помидоры",
    "помидора": "помидоры",
    "помидорчик": "помидоры",
    "помидорчики": "помидоры",
    "томат": "помидоры",
    "томаты": "помидоры",
    "огурец": "огурцы",
    "огурчик": "огурцы",
    "огурчики": "огурцы",
    "яблоко": "яблоки",
    "яблочко": "яблоки",
    "банан": "бананы",
    "апельсин": "апельсины",
    "мандарин": "мандарины",
    "лимон": "лимоны",
    "картошка": "картофель",
    "картоха": "картофель",
    "картофелина": "картофель",
    "морковка": "морковь",
    "морковочка": "морковь",
    "луковица": "лук",
    "лучок": "лук",
    "яичко": "яйца",
    "яйцо": "яйца",
    "яичка": "яйца",
    "молочко": "молоко",
    "творожок": "творог",
    "сметанка": "сметана",
    "курочка": "курица",
    "куриное филе": "филе куриное",
    "куриная грудка": "грудка куриная",
    "куриное бедро": "бедро куриное",
    "бедрышко": "бедро куриное",
    "батончик": "батон",
    "хлебушек": "хлеб",
    "хлебушко": "хлеб",
    "сосиска": "сосиски",
    "сарделька": "сардельки",
    "кефирчик": "кефир",
}


def normalize(text: str) -> str:
    """Lowercase, strip, collapse spaces, apply synonym map."""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s-]", "", t)       # remove stray punctuation
    t = re.sub(r"\s+", " ", t).strip()    # collapse whitespace
    return _NORM_MAP.get(t, t)


def _strip_stop_words(phrase: str) -> str:
    """Remove leading/trailing stop-words from a phrase."""
    words = phrase.split()
    # strip from left
    while words and words[0].lower() in _STOP_WORDS:
        words.pop(0)
    # strip from right
    while words and words[-1].lower() in _STOP_WORDS:
        words.pop()
    return " ".join(words)


_KNOWN_SINGLE_WORDS: set[str] = {
    "яблоки", "яблоко", "бананы", "банан", "апельсины", "апельсин",
    "мандарины", "мандарин", "лимоны", "лимон", "груши", "груша",
    "виноград", "киви", "манго", "ананас", "авокадо", "арбуз", "дыня",
    "помидоры", "помидор", "томаты", "огурцы", "огурец", "черри",
    "картошка", "картофель", "морковь", "морковка", "капуста", "свекла",
    "кабачки", "кабачок", "баклажаны", "баклажан", "перец", "лук", "чеснок",
    "укроп", "петрушка", "кинза", "базилик", "салат", "шпинат", "сельдерей",
    "редис", "тыква", "брокколи", "грибы", "шампиньоны", "имбирь",
    "молоко", "кефир", "ряженка", "йогурт", "творог", "сметана", "сливки",
    "сыр", "масло", "брынза", "моцарелла", "пармезан",
    "рис", "гречка", "макароны", "спагетти", "паста", "лапша",
    "мука", "сахар", "соль", "уксус", "кетчуп", "майонез", "горчица",
    "яйца", "овсянка", "хлопья", "пшено", "чечевица", "нут", "горох",
    "орехи", "семечки", "изюм", "курага",
    "курица", "курочка", "индейка", "свинина", "говядина", "фарш",
    "колбаса", "сосиски", "сардельки", "ветчина", "бекон", "сало",
    "лосось", "сёмга", "семга", "форель", "треска", "минтай", "горбуша",
    "скумбрия", "селёдка", "селедка", "тунец", "кальмары", "креветки",
    "пельмени", "вареники", "наггетсы",
    "вода", "сок", "морс", "компот", "чай", "кофе", "какао", "лимонад",
    "квас", "пиво", "вино",
    "хлеб", "батон", "лаваш", "багет",
    "шоколад", "конфеты", "печенье", "вафли", "торт", "зефир",
    "мармелад", "мёд", "мед", "варенье", "джем", "мороженое",
}


def extract_items(text: str) -> list[str]:
    """Parse user text into individual product names.

    Handles comma-separated, 'и'-separated, and whitespace-separated items.
    Returns list of raw (but trimmed) product names.
    """
    text = text.strip()
    if not text:
        return []

    cleaned = _strip_stop_words(text)
    if not cleaned:
        return []

    has_commas = "," in cleaned
    has_conjunction = re.search(r"\s+и\s+", cleaned) is not None

    if has_commas or has_conjunction:
        parts = re.split(r",", cleaned)
        items: list[str] = []
        for part in parts:
            sub = re.split(r"\s+и\s+", part)
            items.extend(sub)
    else:
        items = _split_by_spaces_smart(cleaned)

    result: list[str] = []
    for item in items:
        item = item.strip().strip(".,;:!?")
        item = re.sub(r"\s+", " ", item).strip()
        if item and item.lower() not in _STOP_WORDS:
            result.append(item)

    return result


def _split_by_spaces_smart(text: str) -> list[str]:
    """Split space-separated text into individual items.

    Tries to treat each word as a separate product if it's in the known
    product dictionary. Otherwise keeps multi-word chunks together.
    """
    words = text.split()
    if len(words) <= 1:
        return words

    all_known = all(w.lower() in _KNOWN_SINGLE_WORDS for w in words)
    if all_known:
        return words

    # If at least 2 out of N words are known products, split individually
    known_count = sum(1 for w in words if w.lower() in _KNOWN_SINGLE_WORDS)
    if known_count >= 2 and known_count >= len(words) * 0.5:
        return words

    return [text]


# ---------------------------------------------------------------------------
# Intent detection: is the message a command or a product list?
# ---------------------------------------------------------------------------

_SHOW_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(покажи|сформируй|выведи|дай|напиши)\s.*список", re.I),
    re.compile(r"список\s*покупок", re.I),
    re.compile(r"что\s+купить", re.I),
    re.compile(r"что\s+в\s+списке", re.I),
]

_CLEAR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(обнули|очисти|сбрось)\s.*список", re.I),
    re.compile(r"(обнули|очисти|сбрось)\s.*покуп", re.I),
    re.compile(r"(удали|убери)\s.*список", re.I),
    re.compile(r"(удали|убери)\s.*покуп", re.I),
]

_REMOVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(удали|убери|убрать|удалить)\s+", re.I),
]

# Single-word commands from voice (Google STT often cuts off "список")
_SHOW_WORDS: set[str] = {
    "покажи", "сформируй", "выведи", "список",
}
_CLEAR_WORDS: set[str] = {
    "обнули", "очисти", "сбрось",
}

_UNDO_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"отмени.*удален", re.I),
    re.compile(r"отмен.*последн", re.I),
    re.compile(r"верни.*обратно", re.I),
    re.compile(r"верни.*назад", re.I),
]
_UNDO_WORDS: set[str] = {
    "отмена", "отмени", "отменить", "верни",
}


def detect_intent(text: str) -> str:
    """Return 'show', 'clear', 'remove', 'undo', or 'add'."""
    t = text.strip()

    for p in _UNDO_PATTERNS:
        if p.search(t):
            return "undo"

    # "clear" must be checked before "remove" because "удали список" = clear
    for p in _CLEAR_PATTERNS:
        if p.search(t):
            return "clear"
    for p in _SHOW_PATTERNS:
        if p.search(t):
            return "show"
    for p in _REMOVE_PATTERNS:
        if p.search(t):
            return "remove"

    low = t.lower().rstrip(".!?, ")
    if low in _UNDO_WORDS:
        return "undo"
    if low in _CLEAR_WORDS:
        return "clear"
    if low in _SHOW_WORDS:
        return "show"

    return "add"


_REMOVE_PREFIX = re.compile(
    r"^(удали|убери|убрать|удалить)\s+", re.I
)


def extract_items_to_remove(text: str) -> list[str]:
    """Strip the remove-verb prefix, then extract item names."""
    cleaned = _REMOVE_PREFIX.sub("", text.strip())
    return extract_items(cleaned)
