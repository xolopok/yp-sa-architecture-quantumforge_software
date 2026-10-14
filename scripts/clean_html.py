"""Чистит скачанные HTML-страницы и собирает исходную базу знаний.

Вход: data/raw/filtered.json и data/raw/pages/*.html (результат fetch_wiki.py).
Выход: knowledge_base/NNN_<имя страницы>.md (по файлу на страницу, YAML
front-matter с сущностями) и knowledge_base/entities.json (каталог файл ->
сущности, исходные имена). knowledge_base/README.md не трогается: файл
редактируется вручную.

Запуск: python clean_html.py
"""

import json
import os
import re

from bs4 import BeautifulSoup, NavigableString, Tag

from common import FILTERED_FILE, KB_DIR, PAGES_DIR

# Секции, целиком не относящиеся к содержанию существа.
DROP_SECTIONS = {"gallery", "history", "soundtrack", "references", "footnotes"}

# Селекторы шума, удаляемые до разбора структуры.
NOISE_SELECTORS = [
    "script",
    "style",
    "div.toc",
    "figure",
    "img",
    "ol.references",
    "div.mw-references",
    "sup.reference",
    "span.reference",
    # navbox-ы: списки всех существ вики внизу страницы
    "[class*=navbox]",
    # Сообщения об ошибках вики-шаблонов: на странице Lennokki секция Drops
    # рендерится как 4992 строки 'Error: String exceeds 1,000 character
    # limit.' вместо списка дропа -- контентной ценности нет.
    "strong.error",
]

# Пункт списка, состоящий только из ссылки (Download:/Instructions: URL):
# внешние ссылки -- шум, а в URL может быть имя вселенной.
LINK_ONLY_ITEM_RE = re.compile(
    r"^(?:download|instructions|links?|sources?|see also|website)\b"
    r"[^a-z]*<?https?://\S+>?\s*(\([^()]*\))?\s*$",
    re.IGNORECASE,
)

# Блоки, проверяемые на упоминание отфильтрованных вариантов.
BLOCK_TAGS = ["p", "li", "dd", "dt", "tr", "h1", "h2", "h3", "h4", "h5", "h6"]

# Поля infobox без текстовой ценности.
INFOBOX_SKIP_FIELDS = {"icon", "image", "image2", "image3"}


def contains_any(tag: Tag, terms: list[str]) -> bool:
    """Проверяет, встречается ли хотя бы один термин в тексте тега (без регистра)."""
    text = tag.get_text().lower()
    return any(term.lower() in text for term in terms)


def remove_noise(root: Tag) -> None:
    """Удаляет шумовые элементы и секции Gallery/History/Soundtrack."""
    for selector in NOISE_SELECTORS:
        for element in root.select(selector):
            element.decompose()
    for heading in root.find_all(["h2", "h3"]):
        title = re.sub(r"\[edit.*$", "", heading.get_text().strip().lower()).strip()
        if title in DROP_SECTIONS:
            for sibling in list(heading.next_siblings):
                if isinstance(sibling, Tag) and sibling.name in ("h1", "h2", "h3"):
                    break
                sibling.extract()
            heading.decompose()


def remove_link_only_items(root: Tag) -> None:
    """Удаляет пункты списков, состоящие только из внешней ссылки."""
    for item in root.find_all("li"):
        text = clean_inline(inline_text(item))
        if LINK_ONLY_ITEM_RE.match(text):
            item.decompose()


def remove_variant_content(root: Tag, removed_terms: list[str]) -> None:
    """Удаляет вкладки infobox и блоки, относящиеся к отфильтрованным вариантам."""
    for aside in root.find_all("aside", class_="portable-infobox"):
        navigation = aside.find("ul", class_="pi-section-navigation")
        if navigation:
            navigation.decompose()
        for section in aside.find_all("div", class_="pi-section-content"):
            if contains_any(section, removed_terms):
                section.decompose()
    # Блочные элементы, содержащие имя или alias варианта. Несколько проходов,
    # так как после удаления детей родитель может остаться с частичным текстом.
    for _ in range(5):
        changed = False
        for tag_name in BLOCK_TAGS:
            for block in root.find_all(tag_name):
                if contains_any(block, removed_terms):
                    block.decompose()
                    changed = True
        for div in root.find_all("div", class_=lambda c: c and "spoiler" in c):
            if contains_any(div, removed_terms):
                div.decompose()
                changed = True
        if not changed:
            break


def inline_text(element) -> str:
    """Собирает инлайновый текст элемента: ссылки и форматирование схлопываются."""
    if isinstance(element, NavigableString):
        return str(element)
    if element.name == "br":
        return " "
    parts = []
    for child in element.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif child.name in ("sup", "style", "script"):
            continue
        else:
            parts.append(inline_text(child))
    return "".join(parts)


def normalize_headings(lines: list[str]) -> list[str]:
    """Ограничивает рост уровней заголовков шагом в один.

    markdownlint MD001 считает заголовок title из front-matter неявным h1,
    поэтому первый заголовок документа должен быть h2, а каждый следующий --
    не глубже предыдущего больше чем на один уровень (страницы вики часто
    начинаются сразу с h3 или пропускают уровни).
    """
    previous = 1  # неявный h1 -- title из front-matter
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6}) ", line)
        if not match:
            continue
        level = min(len(match.group(1)), previous + 1)
        if level != len(match.group(1)):
            lines[index] = "#" * level + line[len(match.group(1)):]
        previous = level
    return lines


def wrap_bare_urls(text: str) -> str:
    """Берёт прямые http(s)-URL в <...> (markdownlint MD034)."""
    return re.sub(r"(?<![(<\[])(https?://\S+)", r"<\1>", text)


def clean_inline(text: str) -> str:
    """Нормализует инлайновый текст: пробелы, \\xa0, pronunciation-маркеры."""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s*\(\s*listen\s*\)\s*", " ", text)
    text = re.sub(r"\s*\(\s*pronunciation unavailable\s*\)\s*", " ", text)
    text = re.sub(r"\s+", " ", text)
    return wrap_bare_urls(text.strip())


def table_to_markdown(table: Tag) -> list[str]:
    """Конвертирует HTML-таблицу в markdown-строки.

    colspan раскрывается в пустые ячейки, строки дополняются до числа
    колонок заголовка (иначе markdownlint MD056), разделитель пишется
    с пробелами -- в едином стиле с ячейками (иначе MD060).

    Особые случаи вики-таблиц: строка-название (th с одной непустой
    ячейкой) выносится в текст перед таблицей; вторая строка заголовков
    после неё идёт строкой данных, разделитель ставится один раз --
    два разделителя подряд делают таблицу невалидной (MD060).
    """
    raw_rows = []
    for tr in table.find_all("tr"):
        cells = []
        for cell in tr.find_all(["th", "td"]):
            text = clean_inline(inline_text(cell))
            colspan = int(cell.get("colspan") or 1)
            cells.extend([text] + [""] * (colspan - 1))
        if cells:
            raw_rows.append((bool(tr.find("th")), cells))
    if not raw_rows:
        return []
    column_count = max(len(cells) for _, cells in raw_rows)

    lines = []
    is_title_row = (
        raw_rows[0][0]
        and sum(1 for cell in raw_rows[0][1] if cell) == 1
        and column_count > 1
    )
    if is_title_row:
        lines.append(next(cell for cell in raw_rows[0][1] if cell))
        lines.append("")
        raw_rows = raw_rows[1:]

    separator_written = False
    for index, (is_header, cells) in enumerate(raw_rows):
        cells += [""] * (column_count - len(cells))
        # Сегмент ячейки ' x '; пустая ячейка -- одиночный пробел ' '
        # (два пробела MD060 считает лишними).
        lines.append("|" + "|".join(
            " " if not cell else f" {cell} " for cell in cells
        ) + "|")
        # Разделитель: после первой строки, даже если в вики нет th-строки
        # (без него markdown не считает строки таблицей, MD058).
        if (is_header or index == 0) and not separator_written:
            lines.append("|" + "|".join([" --- "] * column_count) + "|")
            separator_written = True
    return lines


def list_to_markdown(list_el: Tag, spaces: int = 0) -> list[str]:
    """Конвертирует ul/ol в markdown-список с вложенностью.

    Вложенный список сдвигается на ширину маркера родителя (под '2. ' --
    3 пробела, под '- ' -- 2): при меньшем сдвиге markdown не считает его
    частью пункта (MD032/MD007/MD029).
    """
    lines = []
    ordered = list_el.name == "ol"
    index = 1
    for item in list_el.find_all("li", recursive=False):
        pieces = []
        for child in item.children:
            if isinstance(child, Tag) and child.name in ("ul", "ol"):
                continue
            pieces.append(inline_text(child))
        text = clean_inline("".join(pieces))
        marker = f"{index}. " if ordered else "- "
        if text:
            lines.append(" " * spaces + marker + text)
        if ordered:
            index += 1
        for nested in item.find_all(["ul", "ol"], recursive=False):
            lines.extend(list_to_markdown(nested, spaces + len(marker)))
    return lines


def infobox_to_markdown(aside: Tag) -> list[str]:
    """Конвертирует infobox в строки 'key: value' (по вкладкам).

    Заголовок вкладки (имя сущности) пишется как поле name: выделение
    вместо заголовка (**X**) ловит markdownlint MD036, а на страницах
    с несколькими сущностями оно ещё и не отличает, к какой вкладке
    относятся поля.
    """
    lines = []
    for section in aside.find_all("div", class_="pi-section-content"):
        title = section.find(class_="pi-title")
        if title:
            title_text = clean_inline(title.get_text())
            if title_text:
                lines.append(f"name: {title_text}")
        for item in section.find_all("div", class_="pi-data"):
            # data-source вида 'health4': цифровой суффикс -- номер вкладки
            key = re.sub(r"\d+$", "", item.get("data-source") or "")
            if key in INFOBOX_SKIP_FIELDS:
                continue
            value = item.find(class_="pi-data-value")
            if not value:
                continue
            value_text = clean_inline(inline_text(value))
            if value_text:
                lines.append(f"{key}: {value_text}")
        lines.append("")
    return lines


def block_to_markdown(element: Tag) -> list[str]:
    """Конвертирует блочный элемент в список markdown-строк."""
    if element.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(element.name[1])
        text = re.sub(r"\s*\[edit.*$", "", clean_inline(inline_text(element)))
        return [f"{'#' * level} {text}", ""] if text else []
    if element.name == "p":
        text = clean_inline(inline_text(element))
        return [text, ""] if text else []
    if element.name in ("ul", "ol"):
        return list_to_markdown(element) + [""]
    if element.name == "table":
        return table_to_markdown(element) + [""]
    if element.name == "aside":
        return infobox_to_markdown(element)
    if element.name == "dl":
        lines = []
        for child in element.find_all(["dt", "dd"], recursive=False):
            text = clean_inline(inline_text(child))
            if text:
                lines.append(("* " if child.name == "dt" else ": ") + text)
        return lines + [""]
    # div и прочие контейнеры -- рекурсивно по блочным детям
    lines = []
    for child in element.children:
        if isinstance(child, Tag) and child.name not in ("span", "small", "b", "i"):
            lines.extend(block_to_markdown(child))
    return lines


def drop_empty_sections(lines: list[str]) -> list[str]:
    """Удаляет заголовки, за которыми нет текста до следующего заголовка.

    Возникает после удаления блоков с вариантами: например, секция See Also,
    где все элементы ссылались на удалённые страницы вариантов.
    """
    result = []
    for index, line in enumerate(lines):
        if re.match(r"^#{1,6} ", line):
            rest = re.sub(r"^(?:\s*\n)*", "", "\n".join(lines[index + 1:]))
            if not rest or re.match(r"^#{1,6} ", rest):
                continue
        result.append(line)
    return result


def document_to_markdown(root: Tag) -> str:
    """Собирает markdown документа из блочных элементов корня."""
    lines = []
    for child in root.children:
        if isinstance(child, Tag):
            lines.extend(block_to_markdown(child))
    lines = normalize_headings(drop_empty_sections(lines))
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return text.strip() + "\n"


def yaml_quote(value: str) -> str:
    """Кавычит строку для однострочного значения YAML."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def front_matter(page: str, data: dict) -> str:
    """Готовит YAML front-matter файла: источник, заголовок, сущности."""
    lines = [
        "---",
        f"source: https://noita.wiki.gg/wiki/{data['slug']}",
        f"title: {yaml_quote(page)}",
        "entities:",
    ]
    for entity in data["entities"]:
        lines.append(f"  - name: {yaml_quote(entity['name'])}")
        lines.append(f"    alias: {yaml_quote(entity['alias'])}")
    lines.append("---")
    return "\n".join(lines)


def convert_page(page: str, data: dict, removed_terms: list[str]) -> str:
    """Чистит и конвертирует одну страницу в markdown-текст документа.

    Скобочные синонимы '(also known as X)', '(or X)' не удаляются: имя
    и alias заменяются разными терминами, и после замены фраза
    'термин-1 (also known as термин-2)' сохраняет синонимику сущности.
    """
    html_path = os.path.join(PAGES_DIR, data["slug"] + ".html")
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    root = soup.find("div", class_="mw-parser-output") or soup

    remove_noise(root)
    remove_link_only_items(root)
    remove_variant_content(root, removed_terms)
    return document_to_markdown(root)


def filename_of(number: int, data: dict) -> str:
    """Имя документа по номеру страницы в алфавитном порядке."""
    return f"{number:03d}_{data['slug']}.md"


def build_catalog(pages: dict[str, dict]) -> list[dict]:
    """Готовит записи каталога entities.json по всем страницам."""
    return [
        {
            "file": filename_of(number, data),
            "title": page,
            "source": f"https://noita.wiki.gg/wiki/{data['slug']}",
            "entities": data["entities"],
        }
        for number, (page, data) in enumerate(sorted(pages.items()), 1)
    ]


def reset_kb_dir() -> None:
    """Удаляет старые .md документы базы перед пересборкой.

    README.md не удаляется: файл редактируется вручную.
    """
    os.makedirs(KB_DIR, exist_ok=True)
    for name in os.listdir(KB_DIR):
        if name.endswith(".md") and name != "README.md":
            os.remove(os.path.join(KB_DIR, name))


def main() -> None:
    with open(FILTERED_FILE, encoding="utf-8") as f:
        filtered = json.load(f)
    pages: dict[str, dict] = filtered["pages"]
    removed_terms: list[str] = filtered["removed_terms"]

    reset_kb_dir()
    for number, (page, data) in enumerate(sorted(pages.items()), 1):
        body = convert_page(page, data, removed_terms)
        filename = filename_of(number, data)
        with open(os.path.join(KB_DIR, filename), "w", encoding="utf-8") as f:
            f.write(front_matter(page, data) + "\n\n" + body)

    catalog = build_catalog(pages)
    # Без поля с датой: повторный прогон даёт байт-в-байт тот же файл,
    # что упрощает отладку и проверку воспроизводимости.
    payload = json.dumps(
        {
            "universe": "Noita",
            "wiki": "https://noita.wiki.gg",
            "cargo_table": "Enemies",
            "pages": catalog,
        },
        ensure_ascii=False,
        indent=2,
    )
    with open(os.path.join(KB_DIR, "entities.json"), "w", encoding="utf-8") as f:
        f.write(payload + "\n")

    entities = sum(len(item["entities"]) for item in catalog)
    print(f"Файлов: {len(catalog)} в {KB_DIR}")
    print(f"Сущностей: {entities}")


if __name__ == "__main__":
    main()
