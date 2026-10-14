"""Бенчмарк Qdrant (локальный режим qdrant-client): индексация и поиск.

Важно: упрощенный локальный вариант.

Запуск: python benchmark_qdrant.py
"""

import json
import time

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from common import (
    QUERY_RUNS, TEST_QUERY, TOP_K, embed_query, load_documents,
    load_or_create_embeddings, measure, scale_embeddings, split_into_chunks,
)

BATCH = 1000  # Qdrant не принимает большие пачки за один upsert.


def make_points(start: int, vectors, meta=None):
    """Готовит список точек Qdrant для пачки векторов."""
    points = []
    for i, vector in enumerate(vectors):
        payload = {} if meta is None else dict(meta[start + i])
        points.append(PointStruct(id=start + i, vector=vector.tolist(),
                                  payload=payload))
    return points


def run() -> None:
    documents = load_documents()
    chunks, meta = split_into_chunks(documents)
    embeddings = load_or_create_embeddings(chunks)
    dim = embeddings.shape[1]
    print(f"Чанков: {len(chunks)}\n")

    query_vector = embed_query(TEST_QUERY)
    results = {}

    # --- Основной масштаб: все чанки базы знаний ---
    # Локальный режим в памяти: без сервера и без диска.
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="kb",
        vectors_config=VectorParams(size=dim, distance=Distance.DOT),
    )

    def build_collection():
        for start in range(0, len(embeddings), BATCH):
            client.upsert(collection_name="kb",
                          points=make_points(start, embeddings[start:start + BATCH],
                                             meta=meta))

    build_time, _ = measure("Qdrant (local): добавление точек", build_collection)

    started = time.perf_counter()
    query_result = None
    for _ in range(QUERY_RUNS):
        query_result = client.query_points(
            collection_name="kb", query=query_vector.tolist(), limit=TOP_K)
    query_ms = (time.perf_counter() - started) / QUERY_RUNS * 1000
    print(f"Qdrant (local): поиск top-{TOP_K}: {query_ms:.3f} мс "
          f"(среднее по {QUERY_RUNS} запросам)")
    top1_source = query_result.points[0].payload["source"]
    print(f"Qdrant (local): top-1 документ: {top1_source}")

    results["base"] = {
        "build_ms": round(build_time * 1000, 1),
        "query_ms": round(query_ms, 3),
        "top1": top1_source,
    }

    # --- Масштабный тест: ~10 000 векторов ---
    big_embeddings = scale_embeddings(embeddings)
    print(f"\nМасштабный тест: {len(big_embeddings)} векторов")
    big_client = QdrantClient(":memory:")
    big_client.create_collection(
        collection_name="kb_big",
        vectors_config=VectorParams(size=dim, distance=Distance.DOT),
    )

    def build_big():
        for start in range(0, len(big_embeddings), BATCH):
            big_client.upsert(
                collection_name="kb_big",
                points=make_points(start, big_embeddings[start:start + BATCH]))

    big_build, _ = measure("Qdrant (local): добавление точек", build_big)

    started = time.perf_counter()
    for _ in range(QUERY_RUNS):
        big_client.query_points(collection_name="kb_big",
                                query=query_vector.tolist(), limit=TOP_K)
    big_query_ms = (time.perf_counter() - started) / QUERY_RUNS * 1000
    print(f"Qdrant (local): поиск top-{TOP_K}: {big_query_ms:.3f} мс")

    results["scale_10k"] = {
        "build_ms": round(big_build * 1000, 1),
        "query_ms": round(big_query_ms, 3),
    }

    print("\nИтог (JSON):")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
