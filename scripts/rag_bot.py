"""Консольный RAG-бот по базе знаний QuantumForge Software.

Интерфейс -- REPL: вопрос читается из stdin, `exit` или Ctrl+D/Ctrl+Z
завершают работу. Режим `--ask "вопрос"` задаёт один вопрос и выходит.

Провайдер LLM -- любой OpenAI-совместимый API, конфигурация только
через переменные окружения:

- OPENAI_API_KEY   -- API-ключ (обязателен);
- OPENAI_BASE_URL  -- адрес API; по умолчанию используется официальный
  OpenAI;
- RAG_CHAT_MODEL   -- имя модели, по умолчанию gpt-6-luna.

Запуск: python rag_bot.py [--ask "вопрос"].
"""

import json
import os
import sys
import time

import faiss
import numpy as np
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from sentence_transformers import SentenceTransformer

# Каталог скрипта -- база для всех относительных путей.
HERE = os.path.dirname(os.path.abspath(__file__))
VECTOR_STORE_DIR = os.path.normpath(os.path.join(HERE, "..", "vector_store"))
INDEX_FILE = os.path.join(VECTOR_STORE_DIR, "faiss.index")
META_FILE = os.path.join(VECTOR_STORE_DIR, "meta.json")

# Модель эмбеддингов -- та же, что при построении индекса.
EMBEDDING_MODEL = "BAAI/bge-m3"

# Число найденных чанков и нижняя граница косинусной близости.
# Индекс построен по нормализованным векторам (IndexFlatIP), поэтому score
# -- это косинусная близость. По замерам при построении индекса релевантный
# чанк даёт
# ~0.55, нерелевантные -- 0.47 и ниже; порог 0.40 отсекает шум, но не
# теряет верные документы.
TOP_K = 5
MIN_SCORE = 0.40

# Параметры генерации: низкая температура для фактических ответов,
# запас по токенам на рассуждение и ответ.
MAX_TOKENS = 2000
TEMPERATURE = 0.2

# Повторные попытки при сетевых ошибках и rate limit провайдера.
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5.0

# Имя модели по умолчанию: бюджетная линейка OpenAI (README, раздел 1.1).
DEFAULT_CHAT_MODEL = "gpt-6-luna"

REFUSAL = "Я не знаю -- в базе знаний нет данных по этому вопросу."

# Системный промпт: роль, Chain-of-Thought (сначала шаги, потом ответ),
# grounding на найденные фрагменты и правило отказа (refusal).
SYSTEM_PROMPT = """Ты -- ассистент по корпоративной базе знаний QuantumForge Software.

Правила:
1. Отвечай строго по фрагментам базы знаний, приведённым в сообщении
   пользователя. Не используй собственные знания о похожих мирах и не
   придумывай факты.
2. Если фрагменты не содержат ответа или не относятся к вопросу,
   ответь ровно: {refusal}
3. Сначала опиши шаги рассуждения (1-3 пункта: что спрашивают, что
   нашлось в фрагментах, какой следует вывод), затем дай итоговый ответ
   после слова "Ответ:".
4. В ответе указывай источник в квадратных скобках: [имя файла, чанк N].
5. Отвечай на языке вопроса пользователя.
""".format(refusal=REFUSAL)

# Few-shot примеры. Пары "вопрос -> ответ" составлены
# по документу 001_ostrek_ulkoth.md из базы знаний: первая показывает
# формат успешного ответа с рассуждением и источником, вторая -- формат
# отказа (refusal), когда в базе нет данных.
FEWSHOT_MESSAGES = [
    {
        "role": "user",
        "content": (
            "Найденные фрагменты базы знаний:\n"
            "[1] 001_ostrek_ulkoth.md, чанк 0:\n"
            "The Ostrek Ulkoth (also known as Spirit) are a group of enemies "
            "that apply a status effect to nearby creatures. There are four "
            "spirits: Zentha Nakqir (also known as Nakqir Warden), which "
            "applies Berserk; Ezhara Zenreth (Zenreth Watcher), which applies "
            "Confusion; Drazen Kolnok (Kolnok Shambler), which applies Slimy; "
            "Tavrek Sarreth (Sarreth Skitterer), which applies Weakness. "
            "The Weakness effect will cause creatures to take 10x damage "
            "from most sources.\n\n"
            "Вопрос: Какой дух накладывает эффект берсерк?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Шаги рассуждения:\n"
            "1. В вопросе спрашивают, какой из духов Ostrek Ulkoth накладывает "
            "эффект Berserk.\n"
            "2. В фрагменте [1] перечислены четыре духа и их эффекты: берсерк "
            "указан у Zentha Nakqir.\n"
            "3. Значит, ответ -- Zentha Nakqir.\n"
            "Ответ: Эффект Berserk накладывает дух Zentha Nakqir, известный "
            "также как Nakqir Warden [001_ostrek_ulkoth.md, чанк 0]."
        ),
    },
    {
        "role": "user",
        "content": (
            "Найденные фрагменты базы знаний:\n"
            "[1] 021_ostrek_ulsha.md, чанк 0:\n"
            "Ostrek Ulsha (also known as Ulsha Trapper) is a ghostly white "
            "creature that retaliates when attacked. Each beam deals 8.75 "
            "Holy damage and 14.5 Explosion damage.\n\n"
            "Вопрос: Which spell summons the Ulsha Trapper as an ally?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Шаги рассуждения:\n"
            "1. В вопросе спрашивают о заклинании, призывающем Ulsha Trapper "
            "как союзника.\n"
            "2. В фрагменте [1] описано поведение существа и урон его лучей, "
            "но нет ни одного заклинания призыва.\n"
            "3. Данных для ответа недостаточно, придумывать нельзя.\n"
            "Ответ: {refusal}"
        ).format(refusal=REFUSAL),
    },
]


def load_vector_store() -> tuple["faiss.Index", list[dict]]:
    """Читает FAISS-индекс и метаданные чанков, проверяет их согласованность."""
    if not os.path.exists(INDEX_FILE) or not os.path.exists(META_FILE):
        raise SystemExit(
            "Индекс не найден. Сначала запустите: python build_index.py"
        )
    index = faiss.read_index(INDEX_FILE)
    with open(META_FILE, encoding="utf-8") as f:
        chunks = json.load(f)["chunks"]
    if index.ntotal != len(chunks):
        raise SystemExit(
            f"Индекс и meta.json не согласованы: {index.ntotal} векторов "
            f"против {len(chunks)} чанков. Пересоберите индекс."
        )
    return index, chunks


def search_chunks(
    index: "faiss.Index", chunks: list[dict], encoder: SentenceTransformer, query: str
) -> list[dict]:
    """Ищет top_k ближайших чанков запроса.

    Запрос кодируется той же моделью bge-m3 с нормализацией, что и чанки
    при построении индекса; score в IndexFlatIP -- косинусная близость.
    Чанки ниже MIN_SCORE отбрасываются.
    """
    vector = encoder.encode([query], normalize_embeddings=True).astype(np.float32)
    scores, positions = index.search(vector, TOP_K)
    found = []
    for score, position in zip(scores[0], positions[0]):
        if position == -1 or score < MIN_SCORE:
            continue
        found.append({**chunks[position], "score": float(score)})
    return found


def build_user_message(found: list[dict], query: str) -> str:
    """Собирает сообщение пользователя: найденные чанки + вопрос.

    Каждый чанк помечен номером, источником и номером в документе -- по
    этой маркировке модель цитирует источники в ответе.
    """
    if found:
        blocks = []
        for number, chunk in enumerate(found, start=1):
            text = " ".join(chunk["text"].split())
            blocks.append(f"[{number}] {chunk['source']}, чанк {chunk['chunk']}:\n{text}")
        fragments = "\n\n".join(blocks)
    else:
        fragments = "По запросу ничего не найдено."
    return f"Найденные фрагменты базы знаний:\n{fragments}\n\nВопрос: {query}"


def create_client() -> OpenAI:
    """Создаёт OpenAI-совместимого клиента; ключ обязателен."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "Задайте переменную окружения OPENAI_API_KEY. Дополнительно можно "
            "задать OPENAI_BASE_URL (адрес провайдера) и RAG_CHAT_MODEL "
            f"(по умолчанию {DEFAULT_CHAT_MODEL})."
        )
    return OpenAI(api_key=api_key, timeout=120.0)


def ask_llm(client: OpenAI, model: str, user_message: str) -> str:
    """Отправляет промпт в LLM с повторными попытками при сбоях сети."""
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + FEWSHOT_MESSAGES
        + [{"role": "user", "content": user_message}]
    )
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )
            return response.choices[0].message.content or ""
        except AuthenticationError as error:
            raise SystemExit(
                f"Провайдер отверг API-ключ (OPENAI_API_KEY): {error.message}"
            )
        except (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError) as error:
            if attempt == MAX_ATTEMPTS:
                raise SystemExit(f"Провайдер недоступен после {attempt} попыток: {error}")
            print(
                f"Попытка {attempt} из {MAX_ATTEMPTS} не удалась ({type(error).__name__}), "
                f"повтор через {RETRY_DELAY_SECONDS} с...",
                file=sys.stderr,
            )
            time.sleep(RETRY_DELAY_SECONDS)


def answer(
    index: "faiss.Index",
    chunks: list[dict],
    encoder: SentenceTransformer,
    client: OpenAI,
    model: str,
    query: str,
) -> None:
    """Проводит один запрос через пайплайн RAG и печатает результат."""
    found = search_chunks(index, chunks, encoder, query)
    print(f"\n>>> Вопрос: {query}")
    print(f"Найдено чанков: {len(found)} из {TOP_K} (порог {MIN_SCORE})")
    for chunk in found:
        print(f"  [{chunk['score']:.3f}] {chunk['source']} (чанк {chunk['chunk']})")
    if not found:
        print(f"Ответ: {REFUSAL}")
        return
    user_message = build_user_message(found, query)
    reply = ask_llm(client, model, user_message)
    print(reply)


def main() -> None:
    # Windows-консоль по умолчанию пишет в кодировке cp866/cp1251; без
    # переключения на UTF-8 вывод с кириллицей падает или искажается.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")

    model = os.environ.get("RAG_CHAT_MODEL", DEFAULT_CHAT_MODEL)
    client = create_client()
    print(f"Модель LLM: {model} (OPENAI_BASE_URL: {os.environ.get('OPENAI_BASE_URL') or 'по умолчанию OpenAI'})")

    index, chunks = load_vector_store()
    print(f"Индекс: {index.ntotal} чанков")

    print(f"Загружаю энкодер {EMBEDDING_MODEL}...")
    encoder = SentenceTransformer(EMBEDDING_MODEL)

    arguments = sys.argv[1:]
    if arguments:
        if arguments[0] != "--ask" or len(arguments) < 2:
            raise SystemExit("Использование: python rag_bot.py [--ask \"вопрос\"]")
        answer(index, chunks, encoder, client, model, " ".join(arguments[1:]))
        return

    print("Введите вопрос (exit или Ctrl+D для выхода):")
    while True:
        try:
            query = input("\n> ").strip()
        except EOFError:
            print()
            break
        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            break
        answer(index, chunks, encoder, client, model, query)


if __name__ == "__main__":
    main()
