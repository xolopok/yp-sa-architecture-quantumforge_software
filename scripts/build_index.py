"""Строит векторный индекс базы знаний.

Вход: knowledge_base/*.md (README.md и служебные json-файлы не
индексируются). Выход: vector_store/faiss.index (IndexFlatIP по
нормализованным эмбеддингам bge-m3) и vector_store/meta.json (тексты и
метаданные чанков: источник, заголовок, сущности).

Запуск: python build_index.py [--test]. Флаг --test не строит индекс
заново, а прогоняет тестовые запросы по готовому vector_store/ и
печатает найденные чанки.
"""

import hashlib
import json
import os
import sys
import time

import faiss
import numpy as np
import yaml
from langchain_text_splitters import RecursiveCharacterTextSplitter

from common import KB_DIR

# Каталог скрипта -- база для всех относительных путей.
HERE = os.path.dirname(os.path.abspath(__file__))
VECTOR_STORE_DIR = os.path.normpath(os.path.join(HERE, "..", "vector_store"))
INDEX_FILE = os.path.join(VECTOR_STORE_DIR, "faiss.index")
META_FILE = os.path.join(VECTOR_STORE_DIR, "meta.json")

# Кэш эмбеддингов: ключ -- sha256 модели и текстов чанков, поэтому
# после изменения чанкинга кэш автоматически перестаёт попадать.
CACHE_DIR = os.path.join(HERE, "data", "cache")

# Модель эмбеддингов -- выбор исследования (README, раздел 1.2).
EMBEDDING_MODEL = "BAAI/bge-m3"

# Параметры чанкинга: 1800 символов -- около 300 слов, перекрытие 200.
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 200
SEPARATORS = ["\n## ", "\n\n", ". ", " ", ""]

# Служебные файлы knowledge_base/, не являющиеся документами базы.
SKIP_FILES = {"README.md"}

# Тестовые запросы для --test: два на английском (язык базы), один на
# русском -- проверка кросс-язычного поиска bge-m3.
TEST_QUERIES = [
    "Which spirit applies the Weakness status effect?",
    "Where does the shielded flying drone spawn?",
    "Какой дух накладывает эффект берсерк?",
]
TEST_TOP_K = 5
TEST_SNIPPET = 200


def load_documents() -> list[dict]:
    """Читает документы базы знаний с разобранным front-matter.

    Возвращает список словарей: source (имя файла), title, entities
    (плоский список терминов сущностей) и body без front-matter.
    """
    documents = []
    for name in sorted(os.listdir(KB_DIR)):
        if not name.endswith(".md") or name in SKIP_FILES:
            continue
        with open(os.path.join(KB_DIR, name), encoding="utf-8") as f:
            text = f.read()
        front, body = parse_front_matter(text)
        documents.append(
            {
                "source": name,
                "title": front.get("title", ""),
                "entities": [
                    term
                    for entity in front.get("entities", [])
                    for term in (entity.get("name"), entity.get("alias"))
                    if term
                ],
                "body": body,
            }
        )
    if not documents:
        raise SystemExit(f"База знаний пуста или не найдена: {KB_DIR}")
    return documents


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Отделяет YAML front-matter от тела документа."""
    if not text.startswith("---"):
        return {}, text
    ends = text.find("\n---", 3)
    if ends == -1:
        return {}, text
    front = yaml.safe_load(text[3:ends]) or {}
    return front, text[ends + 4:].lstrip("\n")


def split_into_chunks(documents: list[dict]) -> tuple[list[str], list[dict]]:
    """Разбивает документы на чанки и собирает метаданные.

    Каждый чанк начинается строкой с заголовком документа: у чанков из
    середины секций иначе нет контекста, о какой сущности речь. В
    метаданные идут источник, заголовок, позиция чанка в документе и
    сущности страницы -- по ним бот цитирует источники.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
        keep_separator=True,
    )
    chunks, meta = [], []
    for document in documents:
        pieces = splitter.split_text(document["body"])
        for position, piece in enumerate(pieces):
            if not piece.strip():
                continue
            chunks.append(f"{document['title']}\n\n{piece}")
            meta.append(
                {
                    "id": len(chunks) - 1,
                    "source": document["source"],
                    "title": document["title"],
                    "chunk": position,
                    "entities": document["entities"],
                }
            )
    return chunks, meta


def cache_path(chunks: list[str]) -> str:
    """Путь к файлу кэша эмбеддингов для данных чанков и модели."""
    key = json.dumps([EMBEDDING_MODEL, chunks], ensure_ascii=False)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return os.path.join(CACHE_DIR, f"embeddings_{digest}.npy")


def load_or_create_embeddings(chunks: list[str]) -> tuple[np.ndarray, float]:
    """Считает эмбеддинги чанков (bge-m3, нормализованные).

    При первом запуске эмбеддинги сохраняются в кэш, повторные запуски
    читают его. Возвращает матрицу эмбеддингов и суммарное время
    генерации (0 при попадании в кэш).
    """
    path = cache_path(chunks)
    if os.path.exists(path):
        embeddings = np.load(path)
        print(f"Эмбеддинги из кэша: {embeddings.shape}")
        return embeddings, 0.0

    from sentence_transformers import SentenceTransformer

    print(f"Загружаю модель {EMBEDDING_MODEL} (первый запуск качает ~2.3 ГБ)...")
    started = time.perf_counter()
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"Модель загружена за {time.perf_counter() - started:.1f} с")
    started = time.perf_counter()
    embeddings = model.encode(
        chunks, batch_size=8, normalize_embeddings=True, show_progress_bar=True
    )
    elapsed = time.perf_counter() - started
    print(
        f"Эмбеддинги: {len(chunks)} чанков за {elapsed:.1f} с "
        f"({len(chunks) / elapsed:.2f} чанков/с)"
    )
    embeddings = np.array(embeddings, dtype=np.float32)
    os.makedirs(CACHE_DIR, exist_ok=True)
    np.save(path, embeddings)
    return embeddings, elapsed


def build_index(embeddings: np.ndarray, chunks: list[str], meta: list[dict],
                embedding_seconds: float) -> None:
    """Собирает и сохраняет FAISS-индекс и метаданные чанков.

    Векторы нормализованы, поэтому inner product эквивалентен косинусной
    близости.
    """
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, INDEX_FILE)

    payload = {
        "model": EMBEDDING_MODEL,
        "dimension": int(embeddings.shape[1]),
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedding_seconds": round(embedding_seconds, 1),
        "count": len(chunks),
        "chunks": [{**item, "text": text} for item, text in zip(meta, chunks)],
    }
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(f"Индекс: {index.ntotal} векторов, {embeddings.shape[1]} dim")
    print(f"Файлы: {INDEX_FILE}, {META_FILE}")


def search(query: str, top_k: int = TEST_TOP_K) -> None:
    """Печатает результаты поиска запроса по готовому индексу."""
    from sentence_transformers import SentenceTransformer

    index = faiss.read_index(INDEX_FILE)
    with open(META_FILE, encoding="utf-8") as f:
        chunks = json.load(f)["chunks"]

    model = SentenceTransformer(EMBEDDING_MODEL)
    vector = model.encode([query], normalize_embeddings=True).astype(np.float32)
    scores, positions = index.search(vector, top_k)
    print(f"\nЗапрос: {query}")
    for score, position in zip(scores[0], positions[0]):
        if position == -1:
            continue
        chunk = chunks[position]
        snippet = " ".join(chunk["text"].split())[:TEST_SNIPPET]
        print(
            f"  [{score:.3f}] {chunk['source']} (чанк {chunk['chunk']}) "
            f"-- {snippet}..."
        )


def main() -> None:
    if "--test" in sys.argv[1:]:
        for query in TEST_QUERIES:
            search(query)
        return
    documents = load_documents()
    chunks, meta = split_into_chunks(documents)
    print(f"Документов: {len(documents)}, чанков: {len(chunks)}")
    embeddings, embedding_seconds = load_or_create_embeddings(chunks)
    build_index(embeddings, chunks, meta, embedding_seconds)


if __name__ == "__main__":
    main()
