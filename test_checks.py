# -*- coding: utf-8 -*-
"""Тесты автопроверок: каждая проверка ловит свой типовой дефект и не роняет корректные ответы."""
import sys
import unittest

sys.path.insert(0, ".")
from checks import check_answer

GOOD = """Поливайте фикус Бенджамина зимой умеренно:
- дайте верхнему слою грунта просохнуть на 3–4 см;
- примерно раз в 7–10 дней, в зависимости от температуры;
- используйте отстоянную воду комнатной температуры.

Зимой рост замедляется, и перелив опаснее недолива: в холодной сырой земле корни легко загнивают."""

# Дефект 1: ответ на английском
BAD_LANGUAGE = """Water your ficus once a week in winter. Let the soil dry out between waterings.
- Use room temperature water
- Reduce fertilizing until spring"""

# Дефект 2: нет списка рекомендаций
BAD_FORMAT = """Зимой фикус Бенджамина поливают реже, примерно раз в семь или десять дней, ориентируясь на просыхание верхнего слоя грунта на несколько сантиметров. Вода должна быть отстоянной и комнатной температуры, лишнюю воду из поддона лучше сливать, чтобы не загнили корни.""" + " " * 100

# Дефект 3: зацикливание
BAD_REPETITION = """Уход за фикусом:
- поливайте умеренно
- поливайте умеренно
- поставьте на светлое место

Поливайте умеренно, поливайте умеренно, поливайте умеренно и не забывайте поливать умеренно.""" + " " * 60

# Дефект 4: слишком короткий ответ
BAD_SHORT = "Поливайте реже."

# Дефект 5: слишком длинный ответ (простыня)
BAD_LONG = "Поливайте умеренно. " * 400


class TestChecks(unittest.TestCase):
    def test_good_answer_passes_all(self):
        res = check_answer(GOOD)
        for name in ("language", "list_format", "no_repetition", "length", "passed"):
            self.assertTrue(res[name], f"good answer failed: {name}")

    def test_english_answer_fails_language_only(self):
        res = check_answer(BAD_LANGUAGE)
        self.assertFalse(res["language"])
        self.assertTrue(res["list_format"])
        self.assertFalse(res["passed"])

    def test_no_list_fails_format_only(self):
        res = check_answer(BAD_FORMAT)
        self.assertFalse(res["list_format"])
        self.assertTrue(res["language"])
        self.assertFalse(res["passed"])

    def test_loop_fails_repetition_only(self):
        res = check_answer(BAD_REPETITION)
        self.assertFalse(res["no_repetition"])
        self.assertTrue(res["list_format"])
        self.assertFalse(res["passed"])

    def test_too_short_fails_length(self):
        res = check_answer(BAD_SHORT)
        self.assertFalse(res["length"])
        self.assertFalse(res["passed"])

    def test_too_long_fails_length(self):
        res = check_answer(BAD_LONG)
        self.assertFalse(res["length"])
        self.assertFalse(res["passed"])

    def test_latin_plant_name_does_not_break_language_check(self):
        answer = GOOD.replace("фикус Бенджамина", "орхидею Phalaenopsis")
        self.assertTrue(check_answer(answer)["language"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
