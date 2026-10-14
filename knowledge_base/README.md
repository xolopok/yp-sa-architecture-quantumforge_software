# База знаний: вселенная Noita

База знаний, собранная из открытой вики игры Noita (<https://noita.wiki.gg>). Документы в файлах `*.md`, один файл -- одна сущность/страница вики. Источник: cargo-таблица `Enemies` через MediaWiki API (`https://noita.wiki.gg/api.php?action=cargoquery&tables=Enemies&limit=500&format=json`). Из датасета исключены: weak/hell-варианты (Heikko/Horna...), размерные варианты (Jätti/Pikku/Suur/Iso/Pien...), не-существа (Nest, Death Orb, ...), мета-страницы (Traps, Minä, Pheromone).

## Из чего собрано

Скрипты в `scripts/`: `fetch_wiki.py` (скачивание), `clean_html.py` (чистка и конвертация), `build_terms_map.py` (словарь замен), `replace_terms.py` (замена), `validate_dataset.py` (проверки). Подробности в `scripts/README.md`.
