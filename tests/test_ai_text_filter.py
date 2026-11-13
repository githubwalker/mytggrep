from types import SimpleNamespace

import pytest

from openai import AzureOpenAI

from ai_text_filter import ANSWER_FORMAT, is_yes, make_ai_client, make_ai_filter


class FakeCompletions:
    def __init__(self, answer=None, error=None):
        self.answer = answer
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        message = SimpleNamespace(content=self.answer)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def fake_client(answer=None, error=None):
    completions = FakeCompletions(answer, error)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


@pytest.mark.parametrize("answer", ["yes", "Yes", "YES", " yes\n", "Yes.", '"yes"'])
def test_is_yes_accepts_yes_variants(answer):
    assert is_yes(answer) is True


@pytest.mark.parametrize("answer", ["no", "No.", "", None, "yes, but", "maybe", "yesterday"])
def test_is_yes_rejects_everything_else(answer):
    assert is_yes(answer) is False


@pytest.mark.parametrize(("answer", "expected"), [("Yes", True), ("no", False), (None, False)])
def test_ai_filter_uses_model_answer(answer, expected):
    client, _ = fake_client(answer=answer)
    ai_filter = make_ai_filter(client, "my-deployment", "Is it about rubles?")
    assert ai_filter("куплю рубли") is expected


def test_ai_filter_sends_prompt_text_and_model():
    client, completions = fake_client(answer="yes")
    make_ai_filter(client, "my-deployment", "Is it about rubles?")("куплю рубли")

    (call,) = completions.calls
    assert call["model"] == "my-deployment"
    assert call["messages"] == [
        {"role": "system", "content": f"Is it about rubles?\n\n{ANSWER_FORMAT}"},
        {"role": "user", "content": "куплю рубли"},
    ]


def test_ai_filter_returns_false_on_exception(capsys):
    client, _ = fake_client(error=TimeoutError("boom"))
    ai_filter = make_ai_filter(client, "my-deployment", "Is it about rubles?")
    assert ai_filter("куплю рубли") is False
    assert "TimeoutError: boom" in capsys.readouterr().err


def test_make_ai_client_dated_version_uses_azure_client():
    client = make_ai_client("https://res.openai.azure.com/", "key", "2024-12-01-preview")
    assert isinstance(client, AzureOpenAI)


@pytest.mark.parametrize("version", ["v1", "V1"])
@pytest.mark.parametrize(
    ("endpoint", "base_url"),
    [
        (
            "https://res.services.ai.azure.com/api/projects/proj",
            "https://res.services.ai.azure.com/openai/v1/",
        ),
        ("https://res.openai.azure.com/", "https://res.openai.azure.com/openai/v1/"),
        ("https://res.openai.azure.com", "https://res.openai.azure.com/openai/v1/"),
    ],
)
def test_make_ai_client_v1_uses_v1_base_url(version, endpoint, base_url):
    client = make_ai_client(endpoint, "key", version)
    assert not isinstance(client, AzureOpenAI)
    assert str(client.base_url) == base_url
