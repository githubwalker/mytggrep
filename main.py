import asyncio

# Python 3.14+: asyncio.get_event_loop() no longer creates a loop automatically,
# while Pyrogram 2.0.x calls it at import time. Create the loop beforehand.
asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, filters

from config import env_int, env_list, env_required, to_chat_id
from text_filter import filter_text

API_ID = env_int("API_ID")
API_HASH = env_required("API_HASH")
CHANNELS_TO_MONITOR = [to_chat_id(c) for c in env_list("CHANNELS_TO_MONITOR")]
MY_DESTINATION = to_chat_id(env_required("MY_DESTINATION"))


if not CHANNELS_TO_MONITOR:
    raise SystemExit("Configuration error: CHANNELS_TO_MONITOR is empty")

app = Client("my_account", api_id=API_ID, api_hash=API_HASH)


@app.on_message(filters.chat(CHANNELS_TO_MONITOR) & filters.text)
async def forward_matched_messages(client, message):
    # The OpenAI client is synchronous: run the filters in a thread so Pyrogram keeps receiving messages
    if not await asyncio.to_thread(filter_text, message.text):
        return

    # Форвардим сообщение целиком в ваш канал
    await message.forward(MY_DESTINATION)
    print(f"Message passed PRELIMINARY_FILTER and AI_FILTER and was forwarded to channel {MY_DESTINATION}")


if __name__ == "__main__":
    print("Started successfully! Monitoring the configured channels...")
    app.run()
