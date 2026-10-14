"""Бенчмарк FAISS: скорость индексации, поиска и размер хранилища.

Запуск: python benchmark_faiss.py
"""

import json
import os
import shutil
import time

import faiss
import numpy as np

from common import (
    HERE, QUERY_RUNS, TEST_QUERY, TOP_K, embed_query, load_documents,
    load_or_create_embeddings, measure, scale_embeddings, split_into_chunks,
)

STORAGE_DIR = os.path.join(HERE, "faiss_storage")


def run() -> None:
    documents = load_documents()
    chunks, meta = split_into_chunks(documents)
    embeddings = load_or_create_embeddings(chunks)
    dim = embeddings.shape[1]
    print(f"Чанков: {len(chunks)}, размерность: {dim}\n")

    # Эмбеддинг тестового запроса той же моделью, что и чанки.
    query_vector = embed_query(TEST_QUERY)

    results = {}

    # --- Основной масштаб: все чанки базы знаний ---
    def build_index():
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        return index

    build_time, index = measure("FAISS: построение индекса (IndexFlatIP)", build_index)

    os.makedirs(STORAGE_DIR, exist_ok=True)
    index_path = os.path.join(STORAGE_DIR, "kb.index")

    def save_index():
        faiss.write_index(index, index_path)
        with open(os.path.join(STORAGE_DIR, "meta.json"), "w") as f:
            json.dump(meta, f)

    save_time, _ = measure("FAISS: сохранение на диск", save_index)
    index_size_kib = os.path.getsize(index_path) / 1024
    print(f"FAISS: размер индекса: {index_size_kib:.1f} КиБ")

    load_time, loaded = measure("FAISS: загрузка с диска",
                                lambda: faiss.read_index(index_path))

    def query_index():
        return loaded.search(query_vector.reshape(1, -1), TOP_K)

    started = time.perf_counter()
    for _ in range(QUERY_RUNS):
        _, found = query_index()
    query_ms = (time.perf_counter() - started) / QUERY_RUNS * 1000
    print(f"FAISS: поиск top-{TOP_K}: {query_ms:.3f} мс "
          f"(среднее по {QUERY_RUNS} запросам)")
    top1_source = meta[int(found[0][0])]["source"]
    print(f"FAISS: top-1 документ: {top1_source}")

    results["base"] = {
        "build_ms": round(build_time * 1000, 1),
        "save_ms": round(save_time * 1000, 1),
        "load_ms": round(load_time * 1000, 1),
        "index_kib": round(index_size_kib, 1),
        "query_ms": round(query_ms, 3),
        "top1": top1_source,
    }

    # --- Масштабный тест: ~10 000 векторов ---
    big_embeddings = scale_embeddings(embeddings)
    print(f"\nМасштабный тест: {len(big_embeddings)} векторов")

    def build_big():
        index = faiss.IndexFlatIP(dim)
        index.add(big_embeddings)
        return index

    big_build, big_index = measure("FAISS: построение индекса", build_big)

    started = time.perf_counter()
    for _ in range(QUERY_RUNS):
        big_index.search(query_vector.reshape(1, -1), TOP_K)
    big_query_ms = (time.perf_counter() - started) / QUERY_RUNS * 1000
    print(f"FAISS: поиск top-{TOP_K}: {big_query_ms:.3f} мс")

    results["scale_10k"] = {
        "build_ms": round(big_build * 1000, 1),
        "query_ms": round(big_query_ms, 3),
    }

    print("\nИтог (JSON):")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
