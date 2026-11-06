import asyncio
import json
import os
import re
from pathlib import Path

from openai import AzureOpenAI

from dotenv import load_dotenv

# Python 3.14+: asyncio.get_event_loop() no longer creates a loop automatically,
# while Pyrogram 2.0.x calls it at import time. Create the loop beforehand.
asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, filters

# Настройки читаются из файла .env рядом с main.py (см. .env.example).
# Переменные окружения, заданные явно (например, на VPS), имеют приоритет.
load_dotenv(Path(__file__).with_name(".env"))


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Ошибка конфигурации: переменная {name} не задана (см. .env.example)")
    return value


def env_list(name: str) -> list[str]:
    raw = env_required(name)
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Ошибка конфигурации: {name} должен быть JSON-массивом строк, например [\"a\", \"b\"]: {e}")
    if not isinstance(items, list):
        raise SystemExit(f"Ошибка конфигурации: {name} должен быть JSON-массивом, например [\"a\", \"b\"]")
    # Пустые строки отбрасываем: пустое ключевое слово совпало бы с любым сообщением
    return [str(item).strip() for item in items if str(item).strip()]


def to_chat_id(value: str) -> int | str:
    # Числовые ID ("-100...") должны быть int, иначе фильтр Pyrogram их не сопоставит
    try:
        return int(value)
    except ValueError:
        return value  # @username


def env_int(name: str) -> int:
    raw = env_required(name)
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"Ошибка конфигурации: {name} должен быть числом, получено {raw!r}")


API_ID = env_int("API_ID")
API_HASH = env_required("API_HASH")
CHANNELS_TO_MONITOR = [to_chat_id(c) for c in env_list("CHANNELS_TO_MONITOR")]
MY_DESTINATION = to_chat_id(env_required("MY_DESTINATION"))
KEYWORDS = [k.lower() for k in env_list("KEYWORDS")]

ai_endpoint = env_required("AI_ENDPOINT")
ai_model_name = env_required("AI_MODEL_NAME")
ai_deployment = env_required("AI_DEPLOYMENT")

ai_subscription_key = env_required("AI_SUBSCRIPTION_KEY")
ai_api_version = env_required("AI_API_VERSION")

ai_client = AzureOpenAI(
    api_version=ai_api_version,
    azure_endpoint=ai_endpoint,
    api_key=ai_subscription_key,
)

response = ai_client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "I am going to Paris, what should I see?",
        }
    ],
    max_completion_tokens=16384,
    model=ai_deployment
)


if not CHANNELS_TO_MONITOR:
    raise SystemExit("Ошибка конфигурации: CHANNELS_TO_MONITOR пуст")
if not KEYWORDS:
    raise SystemExit("Ошибка конфигурации: KEYWORDS пуст")

app = Client("my_account", api_id=API_ID, api_hash=API_HASH)


@app.on_message(filters.chat(CHANNELS_TO_MONITOR) & filters.text)
async def forward_matched_messages(client, message):
    text_lower = message.text.lower()

    for word in KEYWORDS:
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            # Форвардим сообщение целиком в ваш канал
            await message.forward(MY_DESTINATION)
            print(f"Сообщение с ключевым словом '{word}' было найдено и должно быть отправлено в канал {MY_DESTINATION}")
            break


if __name__ == "__main__":
    print("Успешно запущено! Мониторю указанные каналы...")
    app.run()
