"""Бенчмарк ChromaDB: скорость индексации, поиска и размер хранилища.

Запуск: python benchmark_chromadb.py
"""

import json
import os
import shutil
import time

import chromadb

from common import (
    HERE, QUERY_RUNS, TEST_QUERY, TOP_K, embed_query, load_documents,
    load_or_create_embeddings, measure, scale_embeddings, split_into_chunks,
)

STORAGE_DIR = os.path.join(HERE, "chromadb_storage")


def measure_query(collection, query_vector, runs):
    """Замеряет среднюю латентность поиска top-K."""
    started = time.perf_counter()
    result = None
    for _ in range(runs):
        result = collection.query(
            query_embeddings=[query_vector.tolist()], n_results=TOP_K)
    elapsed_ms = (time.perf_counter() - started) / runs * 1000
    return elapsed_ms, result


def run() -> None:
    documents = load_documents()
    chunks, meta = split_into_chunks(documents)
    embeddings = load_or_create_embeddings(chunks)
    print(f"Чанков: {len(chunks)}\n")

    query_vector = embed_query(TEST_QUERY)
    results = {}

    # --- Основной масштаб: все чанки базы знаний ---
    shutil.rmtree(STORAGE_DIR, ignore_errors=True)

    def build_collection():
        client = chromadb.PersistentClient(path=STORAGE_DIR)
        collection = client.get_or_create_collection(
            "knowledge_base", metadata={"hnsw:space": "ip"})
        collection.add(
            ids=[f"chunk_{i}" for i in range(len(chunks))],
            documents=chunks,
            metadatas=meta,
            # Передаём готовые векторы bge-m3: сравниваем базы,
            # а не их встроенные эмбеддеры.
            embeddings=embeddings.tolist(),
        )
        return collection

    build_time, collection = measure(
        "ChromaDB: построение коллекции (HNSW, inner product)", build_collection)

    store_size_kib = sum(
        os.path.getsize(os.path.join(root, name))
        for root, _, files in os.walk(STORAGE_DIR) for name in files)
    print(f"ChromaDB: размер хранилища: {store_size_kib / 1024:.1f} КиБ")

    query_ms, query_result = measure_query(collection, query_vector, QUERY_RUNS)
    print(f"ChromaDB: поиск top-{TOP_K}: {query_ms:.3f} мс "
          f"(среднее по {QUERY_RUNS} запросам)")
    top1_source = query_result["metadatas"][0][0]["source"]
    print(f"ChromaDB: top-1 документ: {top1_source}")

    results["base"] = {
        "build_ms": round(build_time * 1000, 1),
        "store_kib": round(store_size_kib / 1024, 1),
        "query_ms": round(query_ms, 3),
        "top1": top1_source,
    }

    # --- Масштабный тест: ~10 000 векторов ---
    big_embeddings = scale_embeddings(embeddings)
    print(f"\nМасштабный тест: {len(big_embeddings)} векторов")
    big_dir = os.path.join(HERE, "chromadb_storage_big")
    shutil.rmtree(big_dir, ignore_errors=True)

    def build_big():
        client = chromadb.PersistentClient(path=big_dir)
        collection = client.get_or_create_collection(
            "knowledge_base_big", metadata={"hnsw:space": "ip"})
        # ChromaDB ограничивает размер одного батча, поэтому
        # добавляем векторами порциями.
        batch = 5000
        big_list = big_embeddings.tolist()
        for start in range(0, len(big_list), batch):
            part = big_list[start:start + batch]
            collection.add(
                ids=[f"chunk_{start + i}" for i in range(len(part))],
                embeddings=part)
        return collection

    big_build, big_collection = measure("ChromaDB: построение коллекции", build_big)
    big_query_ms, _ = measure_query(big_collection, query_vector, QUERY_RUNS)
    print(f"ChromaDB: поиск top-{TOP_K}: {big_query_ms:.3f} мс")

    results["scale_10k"] = {
        "build_ms": round(big_build * 1000, 1),
        "query_ms": round(big_query_ms, 3),
    }

    print("\nИтог (JSON):")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
