"""Split Telegram HTML into chunks that fit the message length limit, each chunk valid HTML."""

import re

_ENTITY_RE = re.compile(r"&#\d+;|&[a-zA-Z]+;")


def _tokenize_html(source: str):
    """Split Telegram-subset HTML into ('tag'|'entity'|'text', payload) tokens.
    Text payloads are already escaped; entities and tags are never split."""
    i, n = 0, len(source)
    while i < n:
        ch = source[i]
        if ch == "<":
            j = i + 1
            quote = None
            while j < n:
                c = source[j]
                if quote:
                    if c == quote:
                        quote = None
                elif c in "\"'":
                    quote = c
                elif c == ">":
                    break
                j += 1
            yield "tag", source[i:j + 1]
            i = j + 1
        elif ch == "&":
            m = _ENTITY_RE.match(source, i)
            if m:
                yield "entity", m.group(0)
                i = m.end()
            else:
                yield "text", "&"
                i += 1
        else:
            j = i
            while j < n and source[j] not in "<&":
                j += 1
            yield "text", source[i:j]
            i = j


def _tag_name(tag: str) -> str:
    body = tag[1:].lstrip("/")
    for k, ch in enumerate(body):
        if ch in " \t\n/>":
            return body[:k]
    return body


def split_html(source: str, limit: int) -> list[str]:
    """Split HTML into chunks of at most `limit` characters (raw markup length;
    conservative, since Telegram counts the parsed text). Open tags are closed
    at the end of each chunk and reopened at the start of the next one, so every
    chunk is valid HTML. Text is split on whitespace when possible."""
    chunks: list[str] = []
    parts: list[str] = []
    length = 0
    open_tags: list[str] = []  # serialized opening tags, in nesting order

    def closing_tags() -> str:
        return "".join(f"</{_tag_name(t)}>" for t in reversed(open_tags))

    def reserved() -> int:
        # every chunk ends with the closing tags of whatever is open at flush
        # time, so that space must be reserved when deciding what fits
        return len(closing_tags())

    def flush() -> None:
        nonlocal parts, length
        chunks.append("".join(parts) + closing_tags())
        parts = list(open_tags)
        length = sum(len(p) for p in parts)

    def emit(piece: str) -> None:
        nonlocal length
        if piece and length + len(piece) > limit - reserved():
            flush()
        parts.append(piece)
        length += len(piece)

    for kind, payload in _tokenize_html(source):
        if kind == "tag":
            if payload.startswith("</"):
                # flush (if any) happens while the tag is still open, so the
                # chunk boundary stays balanced: </x> may land in the new chunk
                emit(payload)
                if open_tags and _tag_name(open_tags[-1]) == _tag_name(payload):
                    open_tags.pop()
            elif payload.endswith("/>"):
                emit(payload)
            else:
                # opening the tag also adds its closer to the reservation;
                # flush beforehand so the tag starts a fresh chunk whole
                closer_len = len(_tag_name(payload)) + 3  # "</x>"
                if length + len(payload) > limit - reserved() - closer_len:
                    flush()
                parts.append(payload)
                length += len(payload)
                open_tags.append(payload)
        elif kind == "entity":
            emit(payload)
        else:  # text, already escaped
            text = payload
            while text:
                room = limit - reserved() - length
                if room <= 0:
                    # pathological nesting: the tags alone fill the limit, so a
                    # flush can't free room — overflow this chunk rather than
                    # loop forever (impossible with real Telegram messages)
                    before = length
                    flush()
                    if length >= before:
                        parts.append(text)
                        length += len(text)
                        break
                    continue
                if len(text) <= room:
                    emit(text)
                    break
                cut = max(text.rfind(" ", 0, room + 1), text.rfind("\n", 0, room + 1))
                if cut <= 0:
                    cut = room  # no whitespace: hard cut
                emit(text[:cut].rstrip())
                flush()
                text = text[cut:].lstrip()

    tail = "".join(parts)
    if tail or not chunks:
        chunks.append(tail + closing_tags())
    return chunks
