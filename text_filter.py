"""Combined text filter: cheap preliminary filter first, then the AI filter.

The AI filter is the one we actually rely on; the preliminary filter only exists
to skip obviously irrelevant texts, so that they never cost an AI call (tokens).

Both filters are configured from .env (PRELIMINARY_FILTER, AI_FILTER, AI_*) when this
module is imported, so configuration errors stop the app at startup.
"""

from openai import AzureOpenAI

from ai_text_filter import make_ai_filter
from config import env_required
from preliminary_text_filter import FilterSyntaxError, compile_filter

# --- Preliminary filter -------------------------------------------------------

PRELIMINARY_FILTER = env_required("PRELIMINARY_FILTER")

try:
    _preliminary_filter = compile_filter(PRELIMINARY_FILTER)
except FilterSyntaxError as e:
    raise SystemExit(f"Configuration error: PRELIMINARY_FILTER: {e}")

# --- AI filter ----------------------------------------------------------------

ai_endpoint = env_required("AI_ENDPOINT")
ai_model_name = env_required("AI_MODEL_NAME")
ai_deployment = env_required("AI_DEPLOYMENT")

ai_subscription_key = env_required("AI_SUBSCRIPTION_KEY")
ai_api_version = env_required("AI_API_VERSION")

ai_client = AzureOpenAI(
    api_version=ai_api_version,
    azure_endpoint=ai_endpoint,
    api_key=ai_subscription_key,
    timeout=60,
)

AI_FILTER = env_required("AI_FILTER")

_ai_filter = make_ai_filter(ai_client, ai_deployment, AI_FILTER)


# --- Public API ---------------------------------------------------------------


def preliminary_filter(text: str) -> bool:
    """Fast substring check against the PRELIMINARY_FILTER expression."""
    return _preliminary_filter(text)


def ai_filter(text: str) -> bool:
    """Ask the AI model the AI_FILTER question about the text; True only if it answers "yes"."""
    return _ai_filter(text)


def filter_text(text: str) -> bool:
    """True only if the text passes both filters.

    The AI filter is called only when the preliminary filter passed.
    Blocking (network call): from async code use ``await asyncio.to_thread(filter_text, text)``.
    """
    if not preliminary_filter(text):
        print(f"Message {text} doesnt match to PRELIMINARY_FILTER")
        return False

    print(f"Message {text} passed PRELIMINARY_FILTER")

    if not ai_filter(text):
        print(f"Message {text} doesnt match to AI_FILTER")
        return False

    print(f"Message {text} passed AI_FILTER")

    return True
