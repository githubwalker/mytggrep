import pytest

import text_filter
from preliminary_text_filter import compile_filter
from text_filter import filter_text


class SpyFilter:
    """Fake filter that returns a fixed result and records the texts it was called with."""

    def __init__(self, result: bool):
        self.result = result
        self.calls: list[str] = []

    def __call__(self, text: str) -> bool:
        self.calls.append(text)
        return self.result


@pytest.fixture
def use_filters(monkeypatch):
    """Replace the configured filters inside text_filter with the given fakes."""

    def install(preliminary, ai):
        monkeypatch.setattr(text_filter, "preliminary_filter", preliminary)
        monkeypatch.setattr(text_filter, "ai_filter", ai)
        return preliminary, ai

    return install


@pytest.mark.parametrize(
    ("preliminary_result", "ai_result", "expected"),
    [(True, True, True), (True, False, False), (False, True, False), (False, False, False)],
)
def test_result_is_true_only_if_both_filters_pass(use_filters, preliminary_result, ai_result, expected):
    use_filters(SpyFilter(preliminary_result), SpyFilter(ai_result))
    assert filter_text("куплю рубли") is expected


@pytest.mark.parametrize("ai_result", [True, False])
def test_ai_filter_not_called_when_preliminary_rejects(use_filters, ai_result):
    preliminary, ai = use_filters(SpyFilter(False), SpyFilter(ai_result))
    filter_text("продам велосипед")
    assert preliminary.calls == ["продам велосипед"]
    assert ai.calls == []


def test_ai_filter_called_once_with_same_text_when_preliminary_passes(use_filters):
    _, ai = use_filters(SpyFilter(True), SpyFilter(True))
    filter_text("Куплю рубли за динары")
    assert ai.calls == ["Куплю рубли за динары"]


def test_with_real_preliminary_filter(use_filters):
    _, ai = use_filters(compile_filter('("КУПЛЮ" or "ищу") and ("рубл" or "RUB")'), SpyFilter(True))

    assert filter_text("куплю рубли") is True
    assert filter_text("продам велосипед") is False
    assert ai.calls == ["куплю рубли"]  # irrelevant text never reached the AI
