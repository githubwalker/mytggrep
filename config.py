"""Settings from the .env file next to this module and from environment variables."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

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
