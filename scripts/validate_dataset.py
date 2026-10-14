"""Проверяет собранную базу знаний (результат clean_html.py / replace_terms.py).

Вход: data/raw/ и knowledge_base/ (режим -- исходные или заменённые
документы -- определяется автоматически по составу файлов).
Выход: отчёт проверок в stdout; код выхода 1 при ошибке.

Запуск: python validate_dataset.py
"""

import json
import os
import re

from common import (
    EXPECTED_STATS,
    FILTERED_FILE,
    KB_DIR,
    MIN_BODY_LENGTH,
    compile_term_pattern,
)

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")
ENTITIES_RAW_FILE = os.path.join(RAW_DIR, "entities.json")
TERMS_MAP_FILE = os.path.join(KB_DIR, "terms_map.json")


def load_front_matter(text: str, path: str) -> tuple[dict, str]:
    """Разбирает YAML front-matter фиксированной схемы clean_html.py.

    Возвращает (метаданные, тело документа). Отсутствие front-matter --
    ValueError.
    """
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise ValueError(f"нет front-matter: {path}")
    header, body = match.groups()
    meta = {"source": None, "title": "", "entities": []}
    current = None
    for line in header.splitlines():
        source = re.match(r"^source: (.+)$", line)
        title = re.match(r'^title: "(.*)"$', line)
        name = re.match(r'^\s*- name: "(.*)"$', line)
        alias = re.match(r'^\s*alias: "(.*)"$', line)
        if source:
            meta["source"] = source.group(1)
        elif title:
            meta["title"] = title.group(1)
        elif name:
            current = {"name": name.group(1), "alias": ""}
            meta["entities"].append(current)
        elif alias and current is not None:
            current["alias"] = alias.group(1)
    return meta, body


def load_documents() -> tuple[dict[str, str], dict[str, dict], dict[str, str], list[str]]:
    """Читает все документы базы, кроме README.md.

    Возвращает (исходные тексты, метаданные, тела, ошибки чтения).
    """
    errors, raws, metas, bodies = [], {}, {}, {}
    for filename in sorted(os.listdir(KB_DIR)):
        if not filename.endswith(".md") or filename == "README.md":
            continue
        path = os.path.join(KB_DIR, filename)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        raws[filename] = text
        try:
            meta, body = load_front_matter(text, filename)
        except ValueError as error:
            errors.append(str(error))
            continue
        metas[filename] = meta
        bodies[filename] = body
    return raws, metas, bodies, errors


def numbered_files() -> set[str]:
    """Все .md документы базы, кроме README.md (он редактируется вручную)."""
    return {
        name for name in os.listdir(KB_DIR)
        if name.endswith(".md") and name != "README.md"
    }


def detect_mode(pages: dict) -> tuple[str, dict[str, str]]:
    """Определяет режим по составу файлов.

    Возвращает (режим, ожидаемое множество файлов). Значения режима --
    ключи: 'original' -- исходные имена страниц, 'replaced' -- термины
    из terms_map.json.
    """
    original = {
        f"{number:03d}_{data['slug']}.md"
        for number, (page, data) in enumerate(sorted(pages.items()), 1)
    }
    actual = numbered_files()
    if actual == original:
        return "original", original

    if os.path.exists(TERMS_MAP_FILE):
        with open(TERMS_MAP_FILE, encoding="utf-8") as f:
            terms_map = json.load(f)
        replaced = {page["new_file"] for page in terms_map["pages"]}
        if actual == replaced:
            return "replaced", replaced
        raise SystemExit(
            f"Состав файлов не совпадает ни с исходным, ни с заменённым; "
            f"лишние {sorted(actual - original)[:5]}..."
        )
    raise SystemExit(
        f"Состав файлов не совпадает с исходным, а terms_map.json нет: "
        f"лишние {sorted(actual - original)[:5]}..."
    )


def expected_entity_terms(pages: dict, terms_map: dict) -> dict[str, dict]:
    """Ожидаемый front-matter заменённых документов.

    Возвращает: имя файла -> {title, entities: [{name, alias}]} --
    все значения в терминах.
    """
    terms = terms_map["terms"]
    result = {}
    for record in terms_map["pages"]:
        data = pages[record["title"]]
        result[record["new_file"]] = {
            "title": record["title_term"],
            "entities": [
                {
                    "name": terms[entity["name"]],
                    "alias": terms.get(entity["alias"], ""),
                }
                for entity in data["entities"]
            ],
        }
    return result


def check_original_front_matter(pages: dict, metas: dict) -> list[str]:
    """Исходный режим: все сущности страницы объявлены в front-matter."""
    errors = []
    for filename, meta in sorted(metas.items()):
        data = pages.get(meta["title"])
        if data is None:
            errors.append(f"{filename}: заголовок '{meta['title']}' не из списка страниц")
            continue
        expected_names = {entity["name"] for entity in data["entities"]}
        got_names = {entity["name"] for entity in meta["entities"]}
        if expected_names != got_names:
            errors.append(
                f"{filename}: сущности не совпадают; "
                f"нет {sorted(expected_names - got_names)}, "
                f"лишние {sorted(got_names - expected_names)}"
            )
    return errors


def check_replaced_front_matter(expected: dict, metas: dict) -> list[str]:
    """Режим замены: front-matter совпадает со словарём, ссылки на вики нет."""
    errors = []
    for filename, meta in sorted(metas.items()):
        want = expected.get(filename)
        if want is None:
            errors.append(f"{filename}: нет в terms_map['pages']")
            continue
        if meta["source"] is not None:
            errors.append(f"{filename}: строка source не удалена")
        if meta["title"] != want["title"]:
            errors.append(f"{filename}: title '{meta['title']}' != '{want['title']}'")
        got = [(e["name"], e["alias"]) for e in meta["entities"]]
        want_entities = [(e["name"], e["alias"]) for e in want["entities"]]
        if got != want_entities:
            errors.append(f"{filename}: сущности не совпадают со словарём замен")
    return errors


def entity_owners(metas: dict) -> dict[str, list[str]]:
    """Распределяет сущности front-matter по файлам."""
    owners: dict[str, list[str]] = {}
    for filename, meta in metas.items():
        for entity in meta["entities"]:
            owners.setdefault(entity["name"], []).append(filename)
    return owners


def find_leftovers(raws: dict[str, str], terms: list[str]) -> list[str]:
    """Ищет исходные термины в текстах; возвращает сообщения.

    Поверх списка терминов добавляются 'noita' и адрес вики в любом
    регистре: термин ASCII и заменялся с учётом регистра, но остаток
    в любом регистре -- утечка.
    """
    scan = list(terms) + ["noita", "noita.wiki.gg"]
    messages = []
    for filename, text in sorted(raws.items()):
        for term in scan:
            pattern = compile_term_pattern(term)
            if term in ("noita", "noita.wiki.gg"):
                pattern = re.compile(pattern.pattern, re.IGNORECASE)
            match = pattern.search(text)
            if match:
                start = max(0, match.start() - 40)
                context = text[start:match.end() + 40].replace("\n", " ")
                messages.append(f"остаток '{term}' в {filename}: ...{context.strip()}...")
    return messages


def check_bodies(metas: dict, bodies: dict[str, str]) -> list[str]:
    """Достаточность тела и упоминание хотя бы одной сущности."""
    warnings = []
    for filename, body in sorted(bodies.items()):
        if len(body) < MIN_BODY_LENGTH:
            warnings.append(f"{filename}: короткое тело ({len(body)} символов)")
        names = [entity["name"] for entity in metas[filename]["entities"]]
        if not any(name.lower() in body.lower() for name in names if name):
            warnings.append(f"{filename}: ни одна сущность не упомянута в теле")
    return warnings


def main() -> None:
    with open(FILTERED_FILE, encoding="utf-8") as f:
        filtered = json.load(f)
    pages: dict[str, dict] = filtered["pages"]
    stats: dict = filtered.get("stats", {})

    errors, warnings = [], []
    for key, expected in EXPECTED_STATS.items():
        if stats.get(key) != expected:
            errors.append(f"stats['{key}'] = {stats.get(key)}, ожидалось {expected}")

    mode, _ = detect_mode(pages)
    raws, metas, bodies, load_errors = load_documents()
    errors += load_errors

    if mode == "original":
        with open(ENTITIES_RAW_FILE, encoding="utf-8") as f:
            raw_rows = json.load(f)
        from fetch_wiki import collect_removed_terms
        removed_terms = collect_removed_terms(raw_rows, pages)
        errors += check_original_front_matter(pages, metas)
        errors += find_leftovers({name: raws[name] for name in raws}, removed_terms)
    else:
        with open(TERMS_MAP_FILE, encoding="utf-8") as f:
            terms_map = json.load(f)
        with open(ENTITIES_RAW_FILE, encoding="utf-8") as f:
            raw_rows = json.load(f)
        from fetch_wiki import collect_removed_terms
        # Полный список исходных терминов: заменённые термины + термины
        # отфильтрованных вариантов (их не должно быть ещё с этапа чистки).
        scan_terms = list(terms_map["terms"]) + collect_removed_terms(raw_rows, pages)
        expected = expected_entity_terms(pages, terms_map)
        errors += check_replaced_front_matter(expected, metas)
        errors += find_leftovers(raws, scan_terms)

    for name, files in sorted(entity_owners(metas).items()):
        if len(files) > 1:
            warnings.append(f"сущность '{name}' в нескольких файлах: {files}")
    warnings += check_bodies(metas, bodies)

    total_entities = sum(len(meta["entities"]) for meta in metas.values())
    mode_labels = {
        "original": "исходные документы",
        "replaced": "заменённые документы",
    }
    print(f"Режим: {mode_labels[mode]}")
    print(f"Файлов: {len(metas)}")
    print(f"Сущностей в front-matter: {total_entities}")
    print(f"Ошибок: {len(errors)}")
    print(f"Предупреждений: {len(warnings)}")
    for message in errors:
        print(f"ОШИБКА: {message}")
    for message in warnings:
        print(f"ВНИМАНИЕ: {message}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
