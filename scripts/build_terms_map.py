"""Строит словарь замен терминов для базы знаний.

Вход: data/raw/filtered.json (результат fetch_wiki.py).
Выход: knowledge_base/terms_map.json.

Запуск: python build_terms_map.py
"""

import hashlib
import json
import os
import re

from common import FILTERED_FILE, KB_DIR

SEED = 42

# Первый корень: из них строится имя. Выдуманные слоги, которых нет в
# словарях реальных языков.
PREFIXES = [
    "Vorak", "Krel", "Drazen", "Ulmar", "Thalven", "Morvek", "Zentha",
    "Kavrik", "Orune", "Belthar", "Sarnel", "Halvox", "Ymrik", "Quorin",
    "Tavrek", "Ezhara", "Rukhel", "Naktoi", "Vessin", "Ostrek", "Mavrok",
    "Silthar", "Grevan", "Duvar", "Kessari",
]

# Второй корень (он же первое слово термин-alias). Голова + хвост,
# комбинаторика даёт 30 x 12 = 360 уникальных корней.
ROOT_HEADS = [
    "dra", "vos", "krel", "mor", "thal", "zen", "kav", "or", "bel", "sar",
    "hal", "ym", "quo", "tav", "ezh", "ruk", "nak", "ves", "ost", "mav",
    "sil", "gre", "du", "kes", "ul", "ith", "kol", "var", "ond", "ern",
]
ROOT_TAILS = [
    "venth", "vaska", "mar", "koth", "reth", "sha", "qir", "vax", "ghor",
    "phis", "nok", "via",
]

# Роль -- второе слово термин-alias. Родовые английские слова, которых
# нет среди исходных терминов (иначе проход замены найдёт роль внутри
# уже заменённого текста).
ROLES = [
    "Marksman", "Warden", "Sentinel", "Stalker", "Marauder", "Watcher",
    "Drifter", "Prowler", "Skitterer", "Lurker", "Shambler", "Howler",
    "Swarmer", "Sapper", "Trapper", "Stinger", "Burrower", "Weaver",
    "Keeper", "Roamer", "Striker", "Glider", "Seeder", "Sifter",
    "Brooder", "Minder", "Shaper", "Herder", "Skulker", "Darter",
]


def pick(digest: bytes, modulus: int, position: int) -> int:
    """Индекс из хеш-дайджеста (по 4 байта на позицию)."""
    offset = (position * 4) % (len(digest) - 4)
    return int.from_bytes(digest[offset:offset + 4], "big") % modulus


class TermPool:
    """Выдаёт уникальные корни и термины по хешу исходного термина."""

    def __init__(self, seed: int = SEED):
        self.seed = seed
        self.used_roots: set[str] = set()
        self.used_words: set[str] = set()
        self.roots: dict[str, str] = {}  # source -> корень из name_term

    def digest(self, source: str, salt: int) -> bytes:
        return hashlib.md5(f"{self.seed}:{salt}:{source}".encode()).digest()

    def root(self, source: str) -> str:
        """Уникальный корень вида 'голова+хвост' (в нижнем регистре)."""
        for salt in range(1000):
            digest = self.digest(source, salt)
            head = ROOT_HEADS[pick(digest, len(ROOT_HEADS), 0)]
            tail = ROOT_TAILS[pick(digest, len(ROOT_TAILS), 1)]
            root = head + tail
            if root not in self.used_roots:
                self.used_roots.add(root)
                return root
        raise RuntimeError(f"не удалось подобрать корень для {source!r}")

    def name_term(self, source: str) -> str:
        """Термин-имя: '<префикс> <корень>'. Корень запоминается по source."""
        digest = self.digest(source, 0)
        prefix = PREFIXES[pick(digest, len(PREFIXES), 0)]
        root = self.root(source).capitalize()
        term = f"{prefix} {root}"
        self.used_words.add(term)
        self.roots[source] = root
        return term

    def alias_term(self, source: str, root: str) -> str:
        """Термин-alias: '<корень> <роль>'; роль выбирается хешем alias."""
        role = ROLES[pick(self.digest(source, 7), len(ROLES), 0)]
        term = f"{root} {role}"
        self.used_words.add(term)
        return term

    def single_word(self, source: str) -> str:
        """Термин из одного слова (вселенная, групповые слова)."""
        root = self.root(source).capitalize()
        self.used_words.add(root)
        return root


def slugify(term: str) -> str:
    """Slug термина для имени файла: 'Vosk Draventh' -> 'vosk_draventh'."""
    return re.sub(r"[^A-Za-z0-9]+", "_", term.lower()).strip("_")


def collect_entities(pages: dict[str, dict]) -> dict[str, dict]:
    """Собирает уникальные сущности по всем страницам.

    Возвращает: name.casefold() -> {name, alias, pages}. Одинаковое имя
    на разных страницах -- одна сущность; alias -- от первой непустой
    строки (страницы обходятся по алфавиту).
    """
    entities: dict[str, dict] = {}
    for page, data in sorted(pages.items()):
        for entry in data["entities"]:
            key = entry["name"].casefold()
            entity = entities.setdefault(
                key, {"name": entry["name"], "alias": "", "pages": []}
            )
            if not entity["alias"] and entry["alias"]:
                entity["alias"] = entry["alias"]
            entity["pages"].append(page)
    return entities


def check_word_collisions(terms: dict[str, str]) -> None:
    """Проверяет, что слова вымышленных терминов не совпадают с исходными.

    Совпадение опасно: проход замены по такому исходному термину нашёл бы
    слово внутри уже заменённого текста и подменил бы его повторно.
    """
    source_words = {
        word for source in terms for word in re.split(r"[^A-Za-z0-9]+", source)
        if word
    }
    fake_words = {
        word for fake in terms.values() for word in fake.split()
    }
    overlap = sorted(source_words & fake_words)
    if overlap:
        raise RuntimeError(f"коллизия слов: {overlap}")


def build_terms_map(pages: dict[str, dict]) -> dict:
    """Собирает содержимое terms_map.json (без записи на диск)."""
    pool = TermPool()
    entities = collect_entities(pages)

    # Термин-имя на каждое уникальное имя (корни уникальны глобально).
    for entity in sorted(entities.values(), key=lambda e: e["name"].casefold()):
        entity["name_term"] = pool.name_term(entity["name"])

    # Термин-alias на каждую уникальную строку alias: корень первого
    # владельца (по алфавиту) + роль от хеша alias.
    alias_terms: dict[str, tuple[str, str]] = {}
    for entity in sorted(entities.values(), key=lambda e: e["name"].casefold()):
        alias = entity["alias"]
        if not alias:
            continue
        if alias not in alias_terms:
            root = pool.roots[entity["name"]]
            alias_terms[alias] = (pool.alias_term(alias, root), entity["name"])

    # Заголовки страниц, не совпадающие ни с одним name, -- групповые
    # страницы (Aave, Gate Guardian): термин-имя из двух слов.
    name_casefolds = set(entities)
    title_terms = {
        page: pool.name_term(f"title:{page}")
        for page in sorted(pages)
        if page.casefold() not in name_casefolds
    }

    universe_term = pool.single_word("Noita")
    hiisi_term = pool.single_word("Hiisi")

    extra_terms = [
        {"source": "Noita", "term": universe_term},
        {"source": "Hiisi", "term": hiisi_term},
        {"source": "Hiidet", "term": hiisi_term},
        *[{"source": title, "term": term} for title, term in sorted(title_terms.items())],
    ]

    # Термин заголовка страницы: у групповых страниц -- доп. термин,
    # у остальных -- термин-имя сущности, совпадающей с заголовком,
    # либо первой сущности страницы.
    page_terms: dict[str, str] = dict(title_terms)
    for page, data in sorted(pages.items()):
        if page in page_terms:
            continue
        key = page.casefold()
        matching = next(
            (e for e in entities.values() if e["name"].casefold() == key), None
        )
        if matching:
            page_terms[page] = matching["name_term"]
        else:
            first = data["entities"][0]["name"].casefold()
            page_terms[page] = entities[first]["name_term"]

    page_records = []
    for number, (page, data) in enumerate(sorted(pages.items()), 1):
        page_records.append({
            "file": f"{number:03d}_{data['slug']}.md",
            "new_file": f"{number:03d}_{slugify(page_terms[page])}.md",
            "title": page,
            "title_term": page_terms[page],
        })

    # Плоский словарь для скрипта замены: source -> fake.
    terms: dict[str, str] = {}
    for entity in sorted(entities.values(), key=lambda e: e["name"].casefold()):
        terms[entity["name"]] = entity["name_term"]
        if entity["alias"]:
            terms[entity["alias"]] = alias_terms[entity["alias"]][0]
    for extra in extra_terms:
        terms[extra["source"]] = extra["term"]
    check_word_collisions(terms)

    entity_records = []
    for entity in sorted(entities.values(), key=lambda e: e["name"].casefold()):
        alias = entity["alias"]
        entity_records.append({
            "name": entity["name"],
            "alias": alias,
            "name_term": entity["name_term"],
            "alias_term": alias_terms[alias][0] if alias else "",
            "shared_alias": bool(alias) and alias_terms[alias][1] != entity["name"],
            "pages": sorted(entity["pages"]),
        })

    return {
        "source_universe": "Noita",
        "universe_term": universe_term,
        "scheme": (
            "у каждой сущности два термина: name -> '<префикс> <корень>', "
            "alias -> '<корень> <роль>'; одинаковые alias получают один "
            "термин-alias"
        ),
        "entities": entity_records,
        "extra_terms": extra_terms,
        "pages": page_records,
        "terms": terms,
    }


def main() -> None:
    with open(FILTERED_FILE, encoding="utf-8") as f:
        filtered = json.load(f)
    terms_map = build_terms_map(filtered["pages"])

    path = os.path.join(KB_DIR, "terms_map.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(terms_map, f, ensure_ascii=False, indent=2)
        f.write("\n")

    entities = terms_map["entities"]
    shared = sum(1 for entity in entities if entity["shared_alias"])
    print(f"Сущностей: {len(entities)}, из них с общим alias: {shared}")
    print(f"Дополнительных терминов: {len(terms_map['extra_terms'])}")
    print(f"Всего пар замены: {len(terms_map['terms'])}")
    print(f"Словарь: {path}")


if __name__ == "__main__":
    main()
