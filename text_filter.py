"""Boolean substring filter for message texts.

Expression syntax (a safe subset of Python, parsed with ``ast``, never executed):

    ("A" or "B") and ("C" or "D") and "X"

* ``"..."``         - true if the text contains this substring (case-insensitive)
* ``and`` / ``or``  - logical operators, parentheses for grouping
* ``not``           - negation, e.g. ``"buy" and not "sell"``
* ``TRUE``/``FALSE`` - match every text / match no text
"""

import ast
from typing import Callable

TextPredicate = Callable[[str], bool]


class FilterSyntaxError(ValueError):
    pass


def compile_filter(expression: str) -> TextPredicate:
    """Parse the expression once and return a fast predicate ``text -> bool``."""
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as e:
        raise FilterSyntaxError(f"invalid filter expression {expression!r}: {e.msg}") from e

    predicate = _compile(tree.body)
    # Substrings are casefolded at compile time, text once per call
    return lambda text: predicate(text.casefold())


def _compile(node: ast.expr) -> TextPredicate:
    match node:
        case ast.BoolOp(op=ast.And(), values=values):
            parts = [_compile(v) for v in values]
            return lambda text: all(p(text) for p in parts)

        case ast.BoolOp(op=ast.Or(), values=values):
            parts = [_compile(v) for v in values]
            return lambda text: any(p(text) for p in parts)

        case ast.UnaryOp(op=ast.Not(), operand=operand):
            inner = _compile(operand)
            return lambda text: not inner(text)

        case ast.Constant(value=str() as substring):
            if not substring:
                raise FilterSyntaxError('empty substring "" is not allowed: it would match every text')
            needle = substring.casefold()
            return lambda text: needle in text

        case ast.Name(id=name) if name.upper() in ("TRUE", "FALSE"):
            result = name.upper() == "TRUE"
            return lambda text: result

        case ast.Constant(value=bool() as result):  # Python-style True / False
            return lambda text: result

        case _:
            raise FilterSyntaxError(
                f"unsupported element {ast.unparse(node)!r}: use quoted strings, "
                f"and/or/not, parentheses, TRUE or FALSE"
            )
