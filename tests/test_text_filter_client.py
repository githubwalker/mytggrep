"""AI client selection from AI_API_VERSION: dated version -> AzureOpenAI, "v1" -> OpenAI on /openai/v1/."""

import importlib

import pytest
from openai import AzureOpenAI

import text_filter


@pytest.fixture
def reload_with(monkeypatch):
    """Reload text_filter with the given env overrides; restore the default config afterwards."""

    def reload(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return importlib.reload(text_filter)

    yield reload
    monkeypatch.undo()
    importlib.reload(text_filter)


def test_dated_api_version_uses_azure_client(reload_with):
    module = reload_with(AI_API_VERSION="2024-12-01-preview")
    assert isinstance(module.ai_client, AzureOpenAI)


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
def test_v1_uses_openai_client_on_v1_base_url(reload_with, version, endpoint, base_url):
    module = reload_with(AI_API_VERSION=version, AI_ENDPOINT=endpoint)
    assert not isinstance(module.ai_client, AzureOpenAI)
    assert str(module.ai_client.base_url) == base_url
