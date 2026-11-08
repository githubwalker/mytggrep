from pathlib import Path

import pytest
from dotenv import dotenv_values

from preliminary_text_filter import FilterSyntaxError, compile_filter


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A C X", True),
        ("B D X", True),
        ("xx-b-d", True),  # substrings, case-insensitive
        ("A C", False),  # no "X"
        ("A X", False),  # neither "C" nor "D"
        ("C D X", False),  # neither "A" nor "B"
        ("", False),
    ],
)
def test_and_of_or_groups(text, expected):
    f = compile_filter('("A" or "B") and ("C" or "D") and "X"')
    assert f(text) is expected


@pytest.mark.parametrize("expr", ["TRUE", "true", "True"])
@pytest.mark.parametrize("text", ["anything", ""])
def test_true_matches_everything(expr, text):
    assert compile_filter(expr)(text) is True


@pytest.mark.parametrize("expr", ["FALSE", "false", "False"])
@pytest.mark.parametrize("text", ["anything", ""])
def test_false_matches_nothing(expr, text):
    assert compile_filter(expr)(text) is False


@pytest.mark.parametrize(
    "text",
    ["приобрету", "ПРИОБРЕТУ", "Приобрету рубли", "куплю", "кУпЛю динары"],
)
def test_uppercase_filter_matches_lowercase_text(text):
    f = compile_filter('("КУПЛЮ" or "ПРИОБРЕТУ")')
    assert f(text) is True


@pytest.mark.parametrize(
    "text",
    ["ПРИОБРЕТУ", "Приобрету", "ПрИоБрЕтУ"],
)
def test_lowercase_filter_matches_uppercase_text(text):
    f = compile_filter('"куплю" or "приобрету"')
    assert f(text) is True


def test_case_insensitive_does_not_match_other_words():
    f = compile_filter('("КУПЛЮ" or "ПРИОБРЕТУ")')
    assert f("продам рубли") is False


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Куплю рубли за ДИНАРЫ", True),
        ("ищу кого-то, rsd наличными", True),
        ("Продам рубли за динары", False),
    ],
)
def test_cyrillic_and_latin_mixed(text, expected):
    f = compile_filter('("куплю" or "ищу") and ("RSD" or "динар")')
    assert f(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("куплю рубли", True), ("продам рубли", False), ("ПРОДАМ РУБЛИ", False)],
)
def test_not(text, expected):
    f = compile_filter('"рубл" and not "продам"')
    assert f(text) is expected


@pytest.mark.parametrize(
    "expr",
    [
        '"A" and',  # syntax error
        '"A" + "B"',  # unsupported operator
        "A or B",  # unquoted words
        '__import__("os").system("ls")',  # code is never executed
        '"A" or ""',  # empty substring
        "",
    ],
)
def test_invalid_expressions_rejected(expr):
    with pytest.raises(FilterSyntaxError):
        compile_filter(expr)


def test_env_example_setting_is_valid():
    """PRELIMINARY_FILTER in .env.example survives .env quoting and compiles."""
    env = dotenv_values(Path(__file__).parent.parent / ".env.example")
    f = compile_filter(env["PRELIMINARY_FILTER"])
    assert f("Куплю рубли за динары") is True
    assert f("Продам велосипед") is False
