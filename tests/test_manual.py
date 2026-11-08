import importlib
from pathlib import Path

from dotenv import dotenv_values
import pytest

import text_filter

#TEST_PRELIMINARY_FILTER='("куплю" or "нужен" or "нужны" or "ищу" or "меняю" or "прода" or "sell" or "buy") and ("rsd" or "dinar" or "динар" or "eur" or "евро" or "€") and ("rub" or "rur" or "рубл" or "р.")'
#TEST_AI_FILTER="return 'yes' only if you see the intention to exchange (euro's or dinars) -> rubles. else return 'no'"


@pytest.fixture(autouse=True)
def use_prod_env(monkeypatch):
    env_path = Path(__file__).parent / "../.env"
    for key, value in dotenv_values(env_path).items():
        if value is not None:
            monkeypatch.setenv(key, value)

    #monkeypatch.setenv('PRELIMINARY_FILTER', TEST_PRELIMINARY_FILTER)
    #monkeypatch.setenv('AI_FILTER', TEST_AI_FILTER)

    importlib.reload(text_filter)
    yield
    importlib.reload(text_filter)


@pytest.skip
@pytest.mark.parametrize("text_to_pass", [
'Белград. Личная встреча продам от 400 до 4000 евро за рубли на карту по курсу 99,90',
'Куплю безналичные рубли за ваши динары. курс 1.29',
])
def test_text_should_pass(text_to_pass: str):
    bok = text_filter.filter_text(text_to_pass)
    assert bok
