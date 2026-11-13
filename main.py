import asyncio
import html

# Python 3.14+: asyncio.get_event_loop() no longer creates a loop automatically,
# while Pyrogram 2.0.x calls it at import time. Create the loop beforehand.
asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, enums, filters, idle

from config import env_int, env_list, env_required, to_chat_id
from html_splitter import split_html
from text_filter import filter_text

API_ID = env_int("API_ID")
API_HASH = env_required("API_HASH")
BOT_TOKEN = env_required("BOT_TOKEN")
CHANNELS_TO_MONITOR = [to_chat_id(c) for c in env_list("CHANNELS_TO_MONITOR")]
MY_DESTINATION = to_chat_id(env_required("MY_DESTINATION"))

MAX_MESSAGE_LENGTH = 4096


if not CHANNELS_TO_MONITOR:
    raise SystemExit("Configuration error: CHANNELS_TO_MONITOR is empty")

app = Client("my_account", api_id=API_ID, api_hash=API_HASH)
# The bot only sends; it must be an admin of MY_DESTINATION with posting rights.
bot = Client("mygrep_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


@app.on_message(filters.chat(CHANNELS_TO_MONITOR) & filters.text)
async def forward_matched_messages(client, message):
    # The OpenAI client is synchronous: run the filters in a thread so Pyrogram keeps receiving messages
    if not await asyncio.to_thread(filter_text, message.text):
        return

    source_name = message.chat.title or message.chat.username or str(message.chat.id)
    header = f'📍 <a href="{html.escape(message.link)}">{html.escape(source_name)}</a>'
    author = author_html(message)
    if author:
        header += f"\n👤 {author}"
    text = f"{header}\n\n{message.text.html}"

    # disable_notification is NOT set: bot messages notify subscribers (that's the point).
    # Long texts are split into valid-HTML chunks, preserving all formatting.
    for chunk in split_html(text, MAX_MESSAGE_LENGTH):
        await bot.send_message(
            MY_DESTINATION,
            chunk,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
    print(f"Message from '{source_name}' passed PRELIMINARY_FILTER and AI_FILTER and was sent to channel {MY_DESTINATION}")


def author_html(message) -> str | None:
    """Author of the message as HTML: a link to the profile when the author has a public username."""
    if message.from_user:
        user = message.from_user
        name = " ".join(filter(None, [user.first_name, user.last_name])) or user.username or str(user.id)
        username = user.username
    elif message.sender_chat:
        if message.sender_chat.id == message.chat.id and not message.author_signature:
            return None
        name = message.author_signature or message.sender_chat.title
        username = message.sender_chat.username
    else:
        return None
    if not name:
        return None
    if username:
        return f'<a href="https://t.me/{html.escape(username)}">{html.escape(name)}</a>'
    return html.escape(name)


async def main():
    await app.start()
    await bot.start()
    print("Started successfully! Monitoring the configured channels...")
    await idle()
    await app.stop()
    await bot.stop()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
