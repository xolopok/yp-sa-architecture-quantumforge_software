"""Применяет словарь замен к документам базы знаний (задание 2).

Вход: knowledge_base/terms_map.json (результат build_terms_map.py) и
исходные документы knowledge_base/NNN_<имя страницы>.md (результат
clean_html.py).
Выход: документы и entities.json заменяются на месте (в терминах,
без ссылок на вики); код выхода 1 при остатках исходных терминов.

Запуск: python replace_terms.py
"""

import json
import os
import re

from common import KB_DIR, compile_term_pattern, replacement_value

ENTITIES_FILE = os.path.join(KB_DIR, "entities.json")
TERMS_MAP_FILE = os.path.join(KB_DIR, "terms_map.json")

SOURCE_LINE_RE = re.compile(r"^source: .*\n", re.MULTILINE)


def load_inputs() -> tuple[dict, dict]:
    """Читает filtered.json (для перезаписи entities.json) и terms_map.json."""
    filtered_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw", "filtered.json")
    with open(filtered_path, encoding="utf-8") as f:
        filtered = json.load(f)
    with open(TERMS_MAP_FILE, encoding="utf-8") as f:
        terms_map = json.load(f)
    return filtered, terms_map


def check_original_state(terms_map: dict) -> None:
    """Документы в базе должны иметь исходные имена из terms_map['pages']."""
    expected = {page["file"] for page in terms_map["pages"]}
    actual = {
        name for name in os.listdir(KB_DIR)
        if name.endswith(".md") and name != "README.md"
    }
    if actual != expected:
        raise SystemExit(
            "Состав документов не совпадает с исходным; замена уже применена "
            "или база пересобрана. Для полной пересборки: clean_html.py -> "
            "build_terms_map.py -> replace_terms.py"
        )


def replace_all(texts: dict[str, str], terms: dict[str, str]) -> tuple[dict[str, str], dict[str, int]]:
    """Применяет замены ко всем текстам; возвращает тексты и счётчик по терминам."""
    counts = {}
    for term in sorted(terms, key=len, reverse=True):
        fake = terms[term]
        pattern = compile_term_pattern(term)
        replaced = 0

        def substitute(match, term=term, fake=fake):
            nonlocal replaced
            replaced += 1
            return replacement_value(term, fake, match)

        for filename, text in texts.items():
            texts[filename] = pattern.sub(substitute, text)
        if replaced:
            counts[term] = replaced
    return texts, counts


def rebuild_entities_json(filtered: dict, terms_map: dict) -> None:
    """Перезаписывает entities.json терминами (без ссылок на вики)."""
    pages = filtered["pages"]
    terms = terms_map["terms"]
    page_records = []
    for record in terms_map["pages"]:
        data = pages[record["title"]]
        page_records.append({
            "file": record["new_file"],
            "title": record["title_term"],
            "entities": [
                {
                    "name": terms[entity["name"]],
                    "alias": terms.get(entity["alias"], ""),
                }
                for entity in data["entities"]
            ],
        })
    payload = json.dumps(
        {
            "universe": terms_map["universe_term"],
            "source_dataset": "knowledge_base/terms_map.json (схема замен)",
            "pages": page_records,
        },
        ensure_ascii=False,
        indent=2,
    )
    with open(ENTITIES_FILE, "w", encoding="utf-8") as f:
        f.write(payload + "\n")


def residual_scan(texts: dict[str, str], terms: dict[str, str]) -> list[str]:
    """Скан остатков: ищет исходные термины в заменённых текстах.

    Поверх плоского словаря: 'noita' в любом регистре (термин ASCII,
    заменялся с учётом регистра) и адрес вики в любом регистре.
    """
    leftovers = []
    scan_terms = dict(terms)
    scan_terms["noita"] = ""
    scan_terms["noita.wiki.gg"] = ""
    for term in sorted(scan_terms, key=len, reverse=True):
        pattern = compile_term_pattern(term)
        if term in ("noita", "noita.wiki.gg"):
            pattern = re.compile(pattern.pattern, re.IGNORECASE)
        for filename, text in sorted(texts.items()):
            match = pattern.search(text)
            if match:
                start = max(0, match.start() - 40)
                context = text[start:match.end() + 40].replace("\n", " ")
                leftovers.append(f"остаток '{term}' в {filename}: ...{context.strip()}...")
    return leftovers


def main() -> None:
    filtered, terms_map = load_inputs()
    check_original_state(terms_map)

    terms = terms_map["terms"]
    page_by_file = {page["file"]: page for page in terms_map["pages"]}

    texts = {}
    for filename in sorted(page_by_file):
        with open(os.path.join(KB_DIR, filename), encoding="utf-8") as f:
            texts[filename] = SOURCE_LINE_RE.sub("", f.read())

    texts, counts = replace_all(texts, terms)
    total = sum(counts.values())
    print(f"Замен выполнено: {total}; терминов с заменами: {len(counts)}")

    for filename, text in texts.items():
        new_file = page_by_file[filename]["new_file"]
        with open(os.path.join(KB_DIR, new_file), "w", encoding="utf-8") as f:
            f.write(text)
        if new_file != filename:
            os.remove(os.path.join(KB_DIR, filename))
    print(f"Документов перезаписано и переименовано: {len(texts)}")

    rebuild_entities_json(filtered, terms_map)
    print("entities.json перезаписан терминами")

    leftovers = residual_scan(texts, terms)
    print(f"Остатков исходных терминов: {len(leftovers)}")
    for message in leftovers:
        print(f"ОСТАТОК: {message}")
    if leftovers:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
