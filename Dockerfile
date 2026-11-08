FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so code changes don't reinstall them
COPY requirements.txt .
RUN pip install -r requirements.txt

# App code
COPY *.py ./

# Settings and Telegram login (see .dockerignore: only these files get into the image)
COPY .env my_account.session ./

# Run as an unprivileged user; it must own /app because the session is a SQLite
# database that Pyrogram writes to (and creates a journal file next to)
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

# No EXPOSE: the app only makes outbound connections (Telegram, Azure OpenAI)
CMD ["python", "main.py"]
