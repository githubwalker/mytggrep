import re
from html.parser import HTMLParser

import pytest

from html_splitter import split_html


class BalanceChecker(HTMLParser):
    """Fails on a closing tag without a matching opener; leftover openers stay in ``stack``."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1] == tag, f"unbalanced </{tag}>"
        self.stack.pop()


def assert_valid_chunks(chunks: list[str], limit: int) -> None:
    for chunk in chunks:
        assert len(chunk) <= limit, chunk
        checker = BalanceChecker()
        checker.feed(chunk)
        checker.close()
        assert checker.stack == [], f"unclosed tags {checker.stack} in {chunk!r}"


def visible_text(html_text: str) -> str:
    return re.sub(r"<[^>]*>", "", html_text)


def test_short_text_is_one_chunk():
    assert split_html("<b>hi</b> there", 4096) == ["<b>hi</b> there"]


def test_empty_text_is_one_empty_chunk():
    assert split_html("", 4096) == [""]


def test_text_splits_on_whitespace():
    chunks = split_html("aaaa bbbb cccc", 10)
    assert chunks == ["aaaa bbbb", "cccc"]


def test_text_without_whitespace_is_hard_cut():
    assert split_html("a" * 25, 10) == ["a" * 10, "a" * 10, "a" * 5]


def test_open_tags_are_closed_and_reopened_across_chunks():
    source = '<b><a href="https://t.me/x">' + "word " * 20 + "</a></b>"
    chunks = split_html(source, 50)
    assert len(chunks) > 1
    assert_valid_chunks(chunks, 50)
    for chunk in chunks:
        assert chunk.startswith('<b><a href="https://t.me/x">')
        assert chunk.endswith("</a></b>")


def test_entities_are_never_split():
    source = "&amp;" * 30
    chunks = split_html(source, 12)
    assert_valid_chunks(chunks, 12)
    assert "".join(chunks) == source
    for chunk in chunks:
        assert re.fullmatch(r"(&amp;)+", chunk)


def test_tag_with_quoted_gt_is_one_token():
    source = '<a href="x>y">link</a>'
    assert split_html(source, 4096) == [source]


@pytest.mark.parametrize("limit", [64, 100, 200, 4096])
def test_long_mixed_message_keeps_text_and_validity(limit):
    source = (
        '📍 <a href="https://t.me/c/1/2">Chat &amp; Co</a>\n👤 Name\n\n'
        + "<b>bold <i>bold italic</i></b> plain &lt;text&gt; " * 15
        + "<pre>code block line</pre>"
    )
    chunks = split_html(source, limit)
    assert_valid_chunks(chunks, limit)
    # nothing lost except whitespace at chunk boundaries
    squash = lambda s: re.sub(r"\s+", "", s)
    assert squash(visible_text("".join(chunks))) == squash(visible_text(source))
