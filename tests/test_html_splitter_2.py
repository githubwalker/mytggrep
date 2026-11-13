"""Tests for html_splitter.split_html.

Run from the project root (where html_splitter.py lives):

    pytest test_html_splitter.py -v
"""

import random
import re
from html.parser import HTMLParser

from html_splitter import split_html

LIMIT = 4096  # real Telegram limit
SMALL = 100   # small limit to keep long-text tests readable


# --- helpers (independent of the module under test) ---------------------------

class _BalanceChecker(HTMLParser):
    """Validates that a chunk is balanced HTML: every opened tag is closed,
    in correct nesting order. Telegram's HTML subset has no void tags."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unexpected </{tag}>, stack: {self.stack}")
        else:
            self.stack.pop()


def visible_text(source: str) -> str:
    """Chunk text without tags, entities decoded."""
    parts = []

    class _TextGrabber(HTMLParser):
        def handle_data(self, data):
            parts.append(data)

    grabber = _TextGrabber(convert_charrefs=True)
    grabber.feed(source)
    grabber.close()
    return "".join(parts)


def compact(source: str) -> str:
    """Visible text with all whitespace removed.

    The splitter may drop whitespace at chunk boundaries (it rstrips/lstrips
    around the split point), so whitespace-insensitive comparison is the right
    check for text preservation.
    """
    return "".join(visible_text(source).split())


def assert_chunks_ok(source: str, limit: int) -> list[str]:
    """The full invariant set every test gets for free."""
    chunks = split_html(source, limit)
    assert chunks, "split_html must return at least one chunk"
    for chunk in chunks:
        assert len(chunk) <= limit, f"chunk of {len(chunk)} chars exceeds limit {limit}: {chunk!r}"
        checker = _BalanceChecker()
        checker.feed(chunk)
        checker.close()
        assert not checker.errors, f"unbalanced chunk {chunk!r}: {checker.errors}"
        assert not checker.stack, f"unclosed tags {checker.stack} in chunk {chunk!r}"
        # entities must never be split: every '&' starts a complete entity
        assert not re.search(r"&(?!#?\w+;)", chunk), f"broken entity in chunk {chunk!r}"
    assert "".join(compact(c) for c in chunks) == compact(source), "visible text changed"
    return chunks


# --- tests --------------------------------------------------------------------

def test_short_text_single_chunk_unchanged():
    source = '<b>привет</b> &amp; пока'
    assert split_html(source, LIMIT) == [source]


def test_empty_input():
    assert split_html("", LIMIT) == [""]


def test_exact_limit_not_split():
    source = "x" * LIMIT
    assert split_html(source, LIMIT) == [source]


def test_long_word_hard_cut():
    source = "x" * 300
    chunks = split_html(source, SMALL)
    assert all(len(c) <= SMALL for c in chunks)
    assert "".join(chunks) == source  # no whitespace anywhere: nothing lost


def test_whitespace_split_keeps_words_whole():
    source = "слово " * 50
    for chunk in split_html(source, SMALL):
        assert all(word == "слово" for word in visible_text(chunk).split())


def test_long_formatted_post_real_limit():
    source = "<b>Важно!</b>\n\n" + (
        'Абзац с <i>форматированием</i> и <a href="https://t.me/example">ссылкой</a>. ' * 10
        + "\n\n"
    ) * 40
    chunks = assert_chunks_ok(source, LIMIT)
    assert len(chunks) > 1


def test_nested_formatting_continues_across_chunks():
    source = "<b>" + "жирный текст " * 30 + "</b>"
    chunks = assert_chunks_ok(source, SMALL)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.startswith("<b>"), f"chunk does not reopen <b>: {chunk!r}"
        assert chunk.endswith("</b>"), f"chunk does not close <b>: {chunk!r}"


def test_tag_at_boundary_moves_to_next_chunk():
    # the blockquote does not fit at the end of the first chunk: it must move whole
    source = "а " * 55 + "<blockquote><b>хвост</b></blockquote>"
    chunks = assert_chunks_ok(source, SMALL + 20)
    assert len(chunks) == 2
    assert chunks[1].startswith("<blockquote>")


def test_entity_at_boundary_not_split():
    source = "b " * 58 + "&amp;" + " c" * 50
    assert_chunks_ok(source, SMALL + 20)


def test_link_with_entity_in_url():
    source = (
        '<a href="https://example.com/path?a=1&amp;b=2">ссылка</a> ' + "текст " * 30
    )
    assert_chunks_ok(source, SMALL)


def test_gt_inside_attribute_value():
    # '>' inside a quoted attribute must not be mistaken for the tag end
    source = '<a href="https://example.com/?q=1&gt;2">метка</a> ' + "слово " * 30
    assert_chunks_ok(source, SMALL)


def test_all_telegram_tags():
    source = (
        "<b>жирный</b> <i>курсив</i> <u>подчёркнутый</u> <s>зачёркнутый</s> "
        "<code>print(x)</code> <pre>блок\nкода</pre> "
        "<blockquote>цитата</blockquote> "
        "<blockquote expandable>длинная цитата</blockquote> "
        "<tg-spoiler>секрет</tg-spoiler> "
        '<span class="tg-spoiler">ещё секрет</span> '
        '<tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>'
    ) + " и дальше текст " * 40
    assert_chunks_ok(source, SMALL)


def test_pathological_nesting_does_not_hang():
    # tags alone exceed the limit: chunks may overflow, but the splitter must
    # terminate and keep the HTML balanced
    source = "<pre>" * 10 + "x " * 200 + "</pre>" * 10
    chunks = split_html(source, SMALL)
    assert chunks
    for chunk in chunks:
        checker = _BalanceChecker()
        checker.feed(chunk)
        checker.close()
        assert not checker.errors and not checker.stack


def test_fuzz_random_documents():
    rng = random.Random(42)
    tags = [
        ("<b>", "</b>"),
        ("<i>", "</i>"),
        ('<a href="https://t.me/example">', "</a>"),
        ("<code>", "</code>"),
        ("<blockquote>", "</blockquote>"),
        ("<tg-spoiler>", "</tg-spoiler>"),
    ]
    words = ["привет", "hello", "данные", "x" * 40, "&amp;", "&lt;3", "123", "\n"]

    for iteration in range(300):
        pieces = []
        for _ in range(rng.randint(5, 60)):
            word = rng.choice(words)
            if rng.random() < 0.35:
                open_tag, close_tag = rng.choice(tags)
                pieces.append(f"{open_tag}{word}{close_tag}")
            else:
                pieces.append(word)
        source = " ".join(pieces)
        limit = rng.randint(50, 300)
        try:
            assert_chunks_ok(source, limit)
        except AssertionError as exc:
            raise AssertionError(
                f"fuzz iteration {iteration} failed (limit={limit}, source={source!r}): {exc}"
            ) from exc
