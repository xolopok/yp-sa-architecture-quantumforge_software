"""Скачивает и фильтрует данные врагов из Noita Wiki (https://noita.wiki.gg).

Выход: data/raw/entities.json (все cargo-строки Enemies),
data/raw/filtered.json (его читают clean_html.py и validate_dataset.py),
data/raw/pages/*.html.

Запуск: python fetch_wiki.py [--force]
"""

import argparse
import json
import os
import re
import time

import requests

from common import ENTITIES_FILE, EXPECTED_STATS, FILTERED_FILE, PAGES_DIR

API = "https://noita.wiki.gg/api.php"
USER_AGENT = "QuantumForge-RAG-coursework/0.1 (educational Python script)"
REQUEST_DELAY = 0.5  # пауза между запросами, чтобы не грузить вики

# Мета-страницы без конкретных существ: ловушки, игрок, феромон.
META_PAGES = {"Traps", "Minä", "Pheromone"}

# Уменьшительные/увеличительные префиксы финских имён.
# "Yli" не включён: Ylialkemisti -- отдельный босс, а не вариант алхимиста.
DIMINUTIVE_RE = re.compile("^(Heikko|Horna|Pikku|Pien|Suur|Iso|Jätti)")

# Суффиксы id, означающие вариант: '<base>_<suffix>' при наличии строки
# '<base>' на той же странице. Суффикс 'big' встречается и склейкой без
# подчёркивания: firebug -> bigfirebug.
VARIANT_ID_SUFFIXES = ("weak", "hell", "big", "small", "tiny")
CONCAT_ID_PREFIXES = ("big",)

# Не-существа в cargo-строках: гнёзда, кристаллы, сферы. Остаются в тексте
# страниц, но не входят в список сущностей для замены.
NON_CREATURE_RE = re.compile("^(Nest|Crystal)$|Orb")

HTML_TAG_RE = re.compile(r"<[^>]+>")
UNOFFICIAL_NAME_RE = re.compile(r"\s*\(Unofficial Name\)\s*$")


def fetch_rows(session: requests.Session) -> list[dict]:
    """Скачивает все строки cargo-таблицы Enemies и сохраняет entities.json."""
    response = session.get(
        API,
        params={
            "action": "cargoquery",
            "tables": "Enemies",
            "fields": "_pageName,name,alias,id,faction,spawnLocation",
            "limit": 500,
            "format": "json",
        },
        timeout=30,
    )
    response.raise_for_status()
    rows = [item["title"] for item in response.json()["cargoquery"]]
    save_json(ENTITIES_FILE, rows)
    return rows


def clean_entity_name(name: str) -> str:
    """Убирает html-разметку и пометку '(Unofficial Name)' из имени сущности."""
    name = HTML_TAG_RE.sub("", name or "").strip()
    return UNOFFICIAL_NAME_RE.sub("", name).strip()


def row_id(row: dict) -> str:
    """Возвращает id строки cargo в нижнем регистре ('' -- если id нет)."""
    return (row.get("id") or "").lower()


def variant_ids(base_id: str) -> set[str]:
    """Собирает все возможные id вариантов для базового id сущности."""
    underscore = {f"{base_id}_{suffix}" for suffix in VARIANT_ID_SUFFIXES}
    concat = {prefix + base_id for prefix in CONCAT_ID_PREFIXES}
    return underscore | concat


def is_id_variant(row: dict, siblings: list[dict]) -> bool:
    """Проверяет признак 'id строки -- это id соседней строки с суффиксом'.

    Примеры: Heikko haulikkohiisi = shotgunner_weak (база shotgunner),
    Suurtulikärpänen = bigfirebug (база firebug).
    """
    return any(
        sibling is not row
        and row_id(sibling)
        and row_id(row) in variant_ids(row_id(sibling))
        for sibling in siblings
    )


def is_alias_variant(row: dict, siblings: list[dict]) -> bool:
    """Проверяет признак 'alias строки -- Weak X/Hell X при наличии alias X'."""
    alias = row.get("alias") or ""
    for prefix in ("Weak ", "Hell "):
        if alias.startswith(prefix):
            base = alias[len(prefix):]
            if any(
                sibling is not row and (sibling.get("alias") or "") == base
                for sibling in siblings
            ):
                return True
    return False


def is_diminutive_variant(row: dict, siblings: list[dict]) -> bool:
    """Проверяет финский уменьшительный/увеличительный префикс имени.

    Исключение -- строка, которая сама является базой пары вариантов на
    своей странице: Pikkutulikärpänen (id firebug) -- базовый светлячок,
    его вариант Suurtulikärpänen имеет id bigfirebug.
    """
    if not DIMINUTIVE_RE.match(clean_entity_name(row.get("name") or "")):
        return False
    is_base = any(
        sibling is not row and row_id(sibling) in variant_ids(row_id(row))
        for sibling in siblings
    )
    return not is_base


def is_variant_row(row: dict, siblings: list[dict]) -> bool:
    """Определяет, является ли строка вариантом базового существа той же страницы."""
    return (
        is_id_variant(row, siblings)
        or is_alias_variant(row, siblings)
        or is_diminutive_variant(row, siblings)
    )


def dedupe(entities: list[dict]) -> list[dict]:
    """Убирает дубликаты сущностей внутри одной страницы.

    Сущности с одинаковым непустым id -- одна и та же игровая сущность
    (пример: Toveri и 'Toveri (Hostile)' имеют id friend). Без id
    дедуплицируются по паре (name, alias).
    """
    seen = set()
    unique = []
    for entity in entities:
        if entity["id"]:
            key = ("id", entity["id"])
        else:
            key = ("pair", entity["name"], entity["alias"])
        if key not in seen:
            seen.add(key)
            unique.append(entity)
    return unique


def split_rows(rows: list[dict]) -> dict[str, dict]:
    """Разбивает cargo-строки на оставшиеся страницы с их сущностями.

    Возвращает словарь: страница -> {"slug", "entities", "others", "removed"}:
    entities -- существа для замены, others -- не-существа (Nest, Orb, ...),
    removed -- отфильтрованные варианты. Страницы без единого существа
    (только варианты) выбрасываются целиком.
    """
    by_page: dict[str, list[dict]] = {}
    for row in rows:
        by_page.setdefault(row["_pageName"], []).append(row)

    kept: dict[str, dict] = {}
    for page, siblings in sorted(by_page.items()):
        if page in META_PAGES:
            continue
        entities, others, removed = [], [], []
        for row in siblings:
            entry = {
                "name": clean_entity_name(row.get("name") or ""),
                "alias": (row.get("alias") or "").strip(),
                "id": (row.get("id") or "").strip(),
            }
            if is_variant_row(row, siblings):
                removed.append(entry)
            elif NON_CREATURE_RE.search(entry["name"]):
                others.append(entry)
            else:
                entities.append(entry)
        entities = dedupe(entities)
        if entities:
            kept[page] = {
                "slug": page.replace(" ", "_"),
                "entities": entities,
                "others": dedupe(others),
                "removed": dedupe(removed),
            }
    return kept


def collect_removed_terms(rows: list[dict], pages: dict[str, dict]) -> list[str]:
    """Собирает имена и alias всех отфильтрованных вариантов.

    Источники: варианты на оставшихся страницах и все creature-строки
    страниц, выброшенных целиком (на них ссылаются другие страницы).
    Мета-страницы и не-существа не входят.
    """
    terms = [
        value
        for data in pages.values()
        for value in [entry["name"] for entry in data["removed"]]
        + [entry["alias"] for entry in data["removed"] if entry["alias"]]
    ]
    kept_values = {
        value
        for data in pages.values()
        for value in [entity["name"] for entity in data["entities"]]
        + [entity["alias"] for entity in data["entities"] if entity["alias"]]
    }
    by_page: dict[str, list[dict]] = {}
    for row in rows:
        by_page.setdefault(row["_pageName"], []).append(row)
    for page, page_rows in by_page.items():
        if page in pages or page in META_PAGES:
            continue
        for row in page_rows:
            name = clean_entity_name(row.get("name") or "")
            if NON_CREATURE_RE.search(name) or name in kept_values:
                continue
            terms.append(name)
            alias = (row.get("alias") or "").strip()
            if alias and alias not in kept_values:
                terms.append(alias)
    return sorted(set(terms))


def build_filtered(rows: list[dict]) -> dict:
    """Собирает содержимое filtered.json: страницы, термины вариантов, статистика.

    Без поля с датой: повторный прогон должен давать байт-в-байт тот же
    файл (файл не коммитится, но стабильность упрощает отладку).
    """
    pages = split_rows(rows)
    return {
        "source": "https://noita.wiki.gg, cargo table Enemies",
        "stats": {
            "raw_rows": len(rows),
            "pages": len(pages),
            "entities": sum(len(data["entities"]) for data in pages.values()),
        },
        "removed_terms": collect_removed_terms(rows, pages),
        "pages": pages,
    }


def save_json(path: str, payload) -> None:
    """Записывает payload в json-файл (utf-8, без экранирования не-ASCII)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def check_stats(stats: dict) -> bool:
    """Сверяет статистику с плановыми объёмами; печатает расхождения."""
    ok = True
    for key, expected in EXPECTED_STATS.items():
        if stats.get(key) != expected:
            print(f"ОШИБКА: {key} = {stats.get(key)}, ожидалось {expected}")
            ok = False
    return ok


def download_page(session: requests.Session, title: str, force: bool) -> None:
    """Скачивает отрендеренный HTML страницы (action=parse&prop=text).

    Уже скачанная страница переиспользуется, кроме случая force=True.
    """
    filename = os.path.join(PAGES_DIR, title.replace(" ", "_") + ".html")
    if os.path.exists(filename) and not force:
        return
    response = session.get(
        API,
        params={
            "action": "parse",
            "page": title,
            "prop": "text",
            "redirects": 1,
            "formatversion": 2,
            "format": "json",
        },
        timeout=30,
    )
    response.raise_for_status()
    with open(filename, "w", encoding="utf-8") as f:
        f.write(response.json()["parse"]["text"])


def download_pages(
    session: requests.Session, titles, force: bool
) -> list[str]:
    """Скачивает страницы по очереди; возвращает список сообщений об ошибках."""
    errors = []
    for index, title in enumerate(sorted(titles), 1):
        try:
            download_page(session, title, force)
        except requests.RequestException as error:
            errors.append(f"{title}: {error}")
            continue
        time.sleep(REQUEST_DELAY)
        if index % 25 == 0:
            print(f"Скачано {index}/{len(titles)} страниц")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="перезакачать уже скачанные страницы")
    args = parser.parse_args()

    os.makedirs(PAGES_DIR, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    rows = fetch_rows(session)
    print(f"Строк в cargo-таблице Enemies: {len(rows)}")

    filtered = build_filtered(rows)
    stats = filtered["stats"]
    print(
        f"После фильтрации: {stats['pages']} страниц, {stats['entities']} сущностей, "
        f"{len(filtered['removed_terms'])} терминов вариантов"
    )
    if not check_stats(stats):
        raise SystemExit(1)
    save_json(FILTERED_FILE, filtered)

    errors = download_pages(session, filtered["pages"], args.force)
    downloaded = len([name for name in os.listdir(PAGES_DIR) if name.endswith(".html")])
    print(f"HTML-файлов в {PAGES_DIR}: {downloaded}")
    for error in errors:
        print(f"ОШИБКА: {error}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
