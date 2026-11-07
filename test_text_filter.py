import unittest
from pathlib import Path

from dotenv import dotenv_values

from text_filter import FilterSyntaxError, compile_filter


class CompileFilterTest(unittest.TestCase):
    def test_and_of_or_groups(self):
        f = compile_filter('("A" or "B") and ("C" or "D") and "X"')
        self.assertTrue(f("A C X"))
        self.assertTrue(f("B D X"))
        self.assertTrue(f("xx-b-d"))  # substrings, case-insensitive
        self.assertFalse(f("A C"))  # no "X"
        self.assertFalse(f("A X"))  # neither "C" nor "D"
        self.assertFalse(f("C D X"))  # neither "A" nor "B"
        self.assertFalse(f(""))

    def test_true_and_false(self):
        for expr in ("TRUE", "true", "True"):
            self.assertTrue(compile_filter(expr)("anything"))
            self.assertTrue(compile_filter(expr)(""))
        for expr in ("FALSE", "false", "False"):
            self.assertFalse(compile_filter(expr)("anything"))

    def test_cyrillic_case_insensitive(self):
        f = compile_filter('("куплю" or "ищу") and ("RSD" or "динар")')
        self.assertTrue(f("Куплю рубли за ДИНАРЫ"))
        self.assertTrue(f("ищу кого-то, rsd наличными"))
        self.assertFalse(f("Продам рубли за динары"))

    def test_not(self):
        f = compile_filter('"рубл" and not "продам"')
        self.assertTrue(f("куплю рубли"))
        self.assertFalse(f("продам рубли"))

    def test_invalid_expressions_rejected(self):
        for expr in (
            '"A" and',  # syntax error
            '"A" + "B"',  # unsupported operator
            "A or B",  # unquoted words
            '__import__("os").system("ls")',  # code is never executed
            '"A" or ""',  # empty substring
            "",
        ):
            with self.subTest(expr=expr), self.assertRaises(FilterSyntaxError):
                compile_filter(expr)


class EnvSettingTest(unittest.TestCase):
    def test_env_example_setting_is_valid(self):
        """PRELIMINARY_FILTER in .env.example survives .env quoting and compiles."""
        env = dotenv_values(Path(__file__).with_name(".env.example"))
        f = compile_filter(env["PRELIMINARY_FILTER"])
        self.assertTrue(f("Куплю рубли за динары"))
        self.assertFalse(f("Продам велосипед"))


if __name__ == "__main__":
    unittest.main()
