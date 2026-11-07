"""AI-based text filter: asks a chat model a yes/no question about the text."""

import sys
from typing import Callable

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

TextPredicate = Callable[[str], bool]

# Appended to the AI_FILTER prompt so the answer is easy to parse
ANSWER_FORMAT = "Respond with exactly one word: yes or no."


def is_yes(answer: str | None) -> bool:
    """True for "yes", "Yes", " YES. " etc.; False for anything else, including None."""
    if not answer:
        return False
    return answer.strip().strip(".!\"'").strip().casefold() == "yes"


def make_ai_filter(client: OpenAI, model: str, prompt: str) -> TextPredicate:
    """Return ``text -> bool`` that is True only if the model answers "yes".

    Any API error (network, timeout, rate limit, content filter...) counts as "no".
    ``client`` may be ``OpenAI`` or ``AzureOpenAI``; for Azure ``model`` is the deployment name.
    """
    system_prompt = f"{prompt.strip()}\n\n{ANSWER_FORMAT}"

    def ai_filter(text: str) -> bool:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        try:
            response = client.chat.completions.create(
                messages=messages,
                max_completion_tokens=16384,
                model=model,
            )
            answer = response.choices[0].message.content
        except Exception as e:
            print(f"AI filter request failed, treating as 'no': {type(e).__name__}: {e}", file=sys.stderr)
            return False
        return is_yes(answer)

    return ai_filter
