"""Settings from the .env file next to this module and from environment variables."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Settings are read from the .env file in the app folder (see .env.example).
# Environment variables set explicitly (e.g. on the VPS) take priority.
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
    # Drop empty strings: an empty item would match every message
    return [str(item).strip() for item in items if str(item).strip()]


def to_chat_id(value: str) -> int | str:
    # Numeric IDs ("-100...") must be int, otherwise the Pyrogram chat filter will not match them
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
