"""pytest setup: fake settings, so tests never depend on your real .env or call Azure.

Runs before test modules are imported. Variables already set in the environment
take priority over .env (load_dotenv does not override them).
"""

import os

os.environ.update(
    {
        "PRELIMINARY_FILTER": "TRUE",
        "AI_ENDPOINT": "https://example.invalid/",
        "AI_MODEL_NAME": "test-model",
        "AI_DEPLOYMENT": "test-deployment",
        "AI_SUBSCRIPTION_KEY": "test-key",
        "AI_API_VERSION": "2024-12-01-preview",
        "AI_FILTER": "Is this a test?",
    }
)
