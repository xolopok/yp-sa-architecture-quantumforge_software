"""Общие пути, константы и правила замены скриптов подготовки базы знаний.

Импортируется остальными скриптами.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

# Промежуточные файлы (data/raw).
RAW_DIR = os.path.join(HERE, "data", "raw")
PAGES_DIR = os.path.join(RAW_DIR, "pages")
ENTITIES_FILE = os.path.join(RAW_DIR, "entities.json")
FILTERED_FILE = os.path.join(RAW_DIR, "filtered.json")

# Готовая база знаний (в корне репозитория).
KB_DIR = os.path.normpath(os.path.join(HERE, "..", "knowledge_base"))

# Плановые объёмы датасета. fetch_wiki.py и validate_dataset.py сверяются
# с ними: расхождение означает, что вики изменилась и датасет перестал
# быть воспроизводимым -- тогда числа нужно обновить осознанно.
EXPECTED_STATS = {
    "raw_rows": 203,   # строк в cargo-таблице Enemies
    "pages": 149,      # страниц существ
    "entities": 168,   # сущностей для замены терминов
}

# Минимальная длина тела документа в validate_dataset.py; более короткие --
# заглушки вики, помечаются предупреждением, а не ошибкой.
MIN_BODY_LENGTH = 300


def compile_term_pattern(term: str) -> re.Pattern:
    """Regex одного термина для замены и скана остатков.

    Границы слов \\b; не-ASCII термины (финские имена) -- без учёта
    регистра, ASCII -- с учётом. Захватывает английские суффиксы s/es
    и финский генитив -n, чтобы они не мешали совпадению.
    """
    body = re.escape(term)
    if term.isascii():
        core = body
    else:
        core = f"(?i:{body})"
    return re.compile(r"\b" + core + r"(?:s|es|n)?")


def replacement_value(term: str, fake: str, match: re.Match) -> str:
    """Текст замены: суффиксы s/es сохраняются, финский генитив -n отбрасывается."""
    suffix = match.group(0)[len(term):]
    return fake + suffix if suffix in ("s", "es") else fake
