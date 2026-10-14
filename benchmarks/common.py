"""Общий модуль для бенчмарков векторных баз.

Содержит генерацию тестовой базы знаний, разбиение документов на чанки,
эмбеддинги (bge-m3) с кэшированием и вспомогательный таймер.
"""

import os
import random
import time

import numpy as np

# Каталог скрипта -- база для всех относительных путей.
HERE = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_DIR = os.path.join(HERE, "knowledge_base")
EMBEDDINGS_CACHE = os.path.join(HERE, "embeddings_cache.npy")

# Модель эмбеддингов: одна и та же для всех сравниваемых баз.
EMBEDDING_MODEL = "BAAI/bge-m3"

# Параметры разбиения документов на чанки (в словах).
CHUNK_SIZE = 400
CHUNK_OVERLAP = 60

# Тестовый запрос: по нему проверяем и корректность, и скорость поиска.
TEST_QUERY = "Who owns HyperRelay and what dashboard should I check first?"

# Сколько раз повторяем поисковый запрос для замера латентности.
QUERY_RUNS = 20
TOP_K = 5

# Целевое число векторов для масштабного теста.
SCALE_TARGET = 10000


def generate_documents() -> None:
    """Создаёт 30 синтетических документов базы знаний (детерминированно).

    Каждый документ -- одна сущность: описание внутреннего сервиса,
    его владельца и регламентов. Имена сущностей повторяются в тексте,
    чтобы поиск мог их находить.
    """
    random.seed(42)
    os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

    services = [
        "HyperRelay", "VoidCore", "QuantumSync", "NexaBridge", "FluxPanel",
        "OrbitGate", "PulseMesh", "DataWeaver", "SignalForge", "GridAnchor",
    ]
    teams = ["Platform", "SRE", "Security", "Data", "Frontend", "Mobile", "QA", "DevOps"]
    topics = [
        "runbook", "architecture decision record", "API reference",
        "onboarding guide", "incident postmortem", "policy",
        "deployment guide", "data model",
    ]
    vocabulary = (
        "the system service deploy pipeline cluster node latency throughput "
        "queue storage cache index replica shard policy access token gateway "
        "endpoint monitor alert dashboard release rollback migration schema "
        "backup restore compliance audit owner review merge branch commit "
        "build test staging production runtime config secret vault "
        "certificate rotation quota limit metric trace log span buffer "
        "stream batch worker scheduler cron retry circuit breaker timeout "
        "backpressure partition leader follower consensus lease epoch "
        "snapshot checkpoint compaction retention ttl eviction"
    ).split()

    for i in range(30):
        service = services[i % len(services)]
        team = teams[i % len(teams)]
        topic = topics[i % len(topics)]
        paragraphs = []
        for _ in range(6):
            words = [random.choice(vocabulary) for _ in range(random.randint(90, 140))]
            # Вставляем имя сущности в случайные позиции, чтобы
            # семантический поиск имел за что зацепиться.
            for pos in random.sample(range(len(words)), k=6):
                words[pos] = service
            text = " ".join(words)
            paragraphs.append(
                f"The {service} {topic} is owned by the {team} team. {text}. "
                f"When operating {service}, always check the {team} dashboard first. "
            )
        document = (
            f"# {service} -- {topic.title()}\n\n"
            f"Owner: {team} team\n\n" + "\n\n".join(paragraphs)
        )
        filename = f"{i:02d}_{service.lower()}_{topic.replace(' ', '_')}.md"
        with open(os.path.join(KNOWLEDGE_BASE_DIR, filename), "w") as f:
            f.write(document)
    print(f"Создано 30 документов в {KNOWLEDGE_BASE_DIR}")


def load_documents() -> list[tuple[str, str]]:
    """Возвращает список пар (имя файла, текст) из базы знаний."""
    if not os.path.isdir(KNOWLEDGE_BASE_DIR):
        raise SystemExit(
            "База знаний не найдена. Сначала запустите "
            "python generate_knowledge_base.py"
        )
    documents = []
    for name in sorted(os.listdir(KNOWLEDGE_BASE_DIR)):
        if name.endswith(".md"):
            with open(os.path.join(KNOWLEDGE_BASE_DIR, name)) as f:
                documents.append((name, f.read()))
    if not documents:
        raise SystemExit("База знаний пуста: нет .md файлов")
    return documents


def split_into_chunks(documents: list[tuple[str, str]]) -> tuple[list[str], list[dict]]:
    """Разбивает документы на перекрывающиеся чанки по словам.

    Возвращает (список текстов чанков, метаданные для каждого чанка).
    Метаданные -- источник (имя файла) и порядковый номер чанка в документе,
    чтобы база могла цитировать источник.
    """
    chunks, meta = [], []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for name, text in documents:
        words = text.split()
        for start in range(0, len(words), step):
            piece = " ".join(words[start:start + CHUNK_SIZE])
            if piece.strip():
                chunks.append(piece)
                meta.append({"source": name, "chunk": start // step})
    return chunks, meta


def load_or_create_embeddings(chunks: list[str]) -> np.ndarray:
    """Возвращает матрицу эмбеддингов чанков (bge-m3, нормализованные).

    При первом запуске считает эмбеддинги и сохраняет в кэш
    (embeddings_cache.npy), при последующих -- читает из кэша, так как
    база знаний детерминирована.
    """
    if os.path.exists(EMBEDDINGS_CACHE):
        embeddings = np.load(EMBEDDINGS_CACHE)
        print(f"Эмбеддинги загружены из кэша: {embeddings.shape}")
        return embeddings

    from sentence_transformers import SentenceTransformer
    print(f"Загружаю модель {EMBEDDING_MODEL} (первый запуск может быть долгим)...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    started = time.perf_counter()
    embeddings = model.encode(
        chunks, batch_size=8, normalize_embeddings=True, show_progress_bar=False)
    elapsed = time.perf_counter() - started
    print(f"Эмбеддинги: {len(chunks)} чанков за {elapsed:.1f} с "
          f"({len(chunks) / elapsed:.2f} чанков/с)")
    embeddings = np.array(embeddings, dtype=np.float32)
    np.save(EMBEDDINGS_CACHE, embeddings)
    return embeddings


def embed_query(query: str) -> np.ndarray:
    """Считает эмбеддинг одного поискового запроса той же моделью."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL)
    vector = model.encode([query], normalize_embeddings=True)
    return np.array(vector, dtype=np.float32)[0]


def measure(label: str, func):
    """Замеряет время выполнения func, печатает результат.

    Возвращает пару (секунды, результат func).
    """
    started = time.perf_counter()
    result = func()
    elapsed = time.perf_counter() - started
    print(f"{label}: {elapsed * 1000:.1f} мс")
    return elapsed, result


def scale_embeddings(embeddings: np.ndarray, target: int = SCALE_TARGET) -> np.ndarray:
    """Копирует эмбеддинги до ~target векторов для масштабного теста.

    Время эмбеддинга не зависит от выбранной векторной базы, поэтому
    для проверки базы на большом объёме достаточно размножить готовые
    векторы с крошечным шумом (чтобы не было точных дубликатов).
    """
    repetitions = max(1, target // len(embeddings))
    scaled = np.tile(embeddings, (repetitions, 1)) + np.random.default_rng(
        0).normal(0, 1e-6, (repetitions * len(embeddings), embeddings.shape[1])
    ).astype(np.float32)
    return scaled
