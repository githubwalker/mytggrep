import asyncio
import json
import os
from pathlib import Path

from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam

from dotenv import load_dotenv

# Python 3.14+: asyncio.get_event_loop() no longer creates a loop automatically,
# while Pyrogram 2.0.x calls it at import time. Create the loop beforehand.
asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, filters

from preliminary_text_filter import FilterSyntaxError, compile_filter

# Настройки читаются из файла .env рядом с main.py (см. .env.example).
# Переменные окружения, заданные явно (например, на VPS), имеют приоритет.
load_dotenv(Path(__file__).with_name(".env"))


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Configuration error: variable {name} is not set (see .env.example)")
    return value


def env_list(name: str) -> list[str]:
    raw = env_required(name)
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Configuration error: {name} must be a JSON array of strings, e.g. [\"a\", \"b\"]: {e}")
    if not isinstance(items, list):
        raise SystemExit(f"Configuration error: {name} must be a JSON array, e.g. [\"a\", \"b\"]")
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
        raise SystemExit(f"Configuration error: {name} must be a number, got {raw!r}")


API_ID = env_int("API_ID")
API_HASH = env_required("API_HASH")
CHANNELS_TO_MONITOR = [to_chat_id(c) for c in env_list("CHANNELS_TO_MONITOR")]
MY_DESTINATION = to_chat_id(env_required("MY_DESTINATION"))
PRELIMINARY_FILTER = env_required("PRELIMINARY_FILTER")

try:
    _preliminary_filter = compile_filter(PRELIMINARY_FILTER)
except FilterSyntaxError as e:
    raise SystemExit(f"Configuration error: PRELIMINARY_FILTER: {e}")


def preliminary_filter(text: str) -> bool:
    """Быстрая проверка текста по выражению PRELIMINARY_FILTER из .env."""
    return _preliminary_filter(text)

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

messages: list[ChatCompletionMessageParam] = [
    {
        "role": "system",
        "content": "please response yes or no if text contains wish to buy rubles (RUB) in exchange of dinars (RSD)",
    },
    {
        "role": "user",
        #"content": "will buy you rubles in exchange of my dinars",
        # "content": "I have a little bit of dinars want to exchange on you rubles. google current exchange rate ",
        "content": "I have a little rubles. need to buy you dinars",
    },
]

response = ai_client.chat.completions.create(
    messages=messages,
    max_completion_tokens=16384,
    model=ai_deployment
)

print(f'does user want to buy rubles in exchange of dinars? {response.choices[0].message.content}')

if not CHANNELS_TO_MONITOR:
    raise SystemExit("Configuration error: CHANNELS_TO_MONITOR is empty")

app = Client("my_account", api_id=API_ID, api_hash=API_HASH)


@app.on_message(filters.chat(CHANNELS_TO_MONITOR) & filters.text)
async def forward_matched_messages(client, message):
    if preliminary_filter(message.text):
        # Форвардим сообщение целиком в ваш канал
        await message.forward(MY_DESTINATION)
        print(f"Message passed PRELIMINARY_FILTER and was forwarded to channel {MY_DESTINATION}")


if __name__ == "__main__":
    print("Started successfully! Monitoring the configured channels...")
    app.run()
