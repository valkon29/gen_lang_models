# -*- coding: utf-8 -*-
"""Автоматические проверки ответов ассистента по теме «Домашние растения».

Критерии и их обоснование для нашей темы:

1. Язык — русский. Пользователь задаёт вопросы по-русски; instruct-модели
   при дообучении на смешанных данных нередко «переключаются» на английский.
   Порог — доля кириллицы среди букв ≥ 0.5 (в ответах легитимно встречаются
   латинские названия растений, например Phalaenopsis).

2. Формат — рекомендации списком. Для темы «уход за растениями» ответ
   из сплошного текста плохо читается: пользователь сканирует глазами
   пункты («полив», «свет», «пересадка»). Требуем ≥ 2 пунктов списка.

3. Отсутствие повторений. Типовая деградация при SFT на маленьком
   датасете — зацикливание («Поливайте умеренно. Поливайте умеренно...»).
   Ловим повторы строк, предложений и 5-словных шинглов.

4. Длина — 150…2500 символов. Пустой или односложный ответ бесполезен,
   «простыня» на 5000 символов не читается.

Использование:
    python checks.py answers.jsonl          # проверить файл
    python checks.py answers.jsonl --key answer   # если поле называется не "answer"
"""

import argparse
import json
import re
import sys
from collections import Counter

CYRILLIC_RE = re.compile(r"[а-яё]", re.IGNORECASE)
LATIN_RE = re.compile(r"[a-z]", re.IGNORECASE)
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*•–]|\d+[.)])\s+\S", re.MULTILINE)
SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")
SHINGLE_SIZE = 5

MIN_LEN, MAX_LEN = 150, 2500
MIN_LIST_ITEMS = 2
MAX_DUP_SENTENCES = 0
MAX_SHINGLE_REPEATS = 2


def _letters(text: str) -> str:
    return "".join(CYRILLIC_RE.findall(text) + LATIN_RE.findall(text))


def check_language(answer: str) -> bool:
    """Доля кириллицы среди букв ≥ 0.5 и букв хотя бы 20."""
    letters = _letters(answer)
    if len(letters) < 20:
        return False
    cyr = len(CYRILLIC_RE.findall(answer))
    return cyr / len(letters) >= 0.5


def check_list_format(answer: str) -> bool:
    """В ответе есть список рекомендаций (≥ 2 пунктов)."""
    return len(LIST_ITEM_RE.findall(answer)) >= MIN_LIST_ITEMS


def check_no_repetition(answer: str) -> bool:
    """Нет повторяющихся строк/предложений и зацикленных фраз."""
    # 1) одинаковые непустые строки
    lines = [ln.strip().lower() for ln in answer.splitlines() if len(ln.strip()) >= 10]
    if any(c > 1 for c in Counter(lines).values()):
        return False
    # 2) одинаковые предложения
    sentences = [s.strip().lower() for s in SENTENCE_SPLIT_RE.split(answer) if len(s.strip()) >= 10]
    if sum(c - 1 for c in Counter(sentences).values() if c > 1) > MAX_DUP_SENTENCES:
        return False
    # 3) повторяющиеся 5-словные шинглы (ловит «хвост-зацикливание»)
    words = re.findall(r"[а-яёa-z]+", answer.lower())
    shingles = Counter(tuple(words[i:i + SHINGLE_SIZE]) for i in range(len(words) - SHINGLE_SIZE + 1))
    return all(c <= MAX_SHINGLE_REPEATS for c in shingles.values())


def check_length(answer: str) -> bool:
    return MIN_LEN <= len(answer.strip()) <= MAX_LEN


CHECKS = {
    "language": check_language,
    "list_format": check_list_format,
    "no_repetition": check_no_repetition,
    "length": check_length,
}


def check_answer(answer: str) -> dict:
    """Возвращает словарь {проверка: bool} + агрегированный вердикт."""
    result = {name: fn(answer) for name, fn in CHECKS.items()}
    result["passed"] = all(result.values())
    return result


def check_file(path: str, key: str = "answer") -> dict:
    """Проверяет jsonl-файл; возвращает сводку по каждой проверке и по записям."""
    per_check = {name: 0 for name in CHECKS}
    total = 0
    failures = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            answer = rec[key] if key in rec else rec.get("messages", [{}])[-1].get("content", "")
            res = check_answer(answer)
            total += 1
            for name in CHECKS:
                per_check[name] += res[name]
            if not res["passed"]:
                failures.append((i, [k for k in CHECKS if not res[k]]))
    return {"total": total, "per_check": per_check, "failures": failures}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="jsonl-файл с ответами")
    parser.add_argument("--key", default="answer", help="имя поля с ответом (default: answer)")
    args = parser.parse_args()

    summary = check_file(args.path, key=args.key)
    print(f"Файл: {args.path} | ответов: {summary['total']}\n")
    for name, ok in summary["per_check"].items():
        rate = ok / summary["total"] if summary["total"] else 0
        print(f"  {name:<14} {ok:>4}/{summary['total']}  ({rate:.0%})")
    if summary["failures"]:
        print("\nНе прошли:")
        for i, bad in summary["failures"][:20]:
            print(f"  строка {i}: {', '.join(bad)}")
    else:
        print("\nВсе ответы прошли проверки ✅")
    sys.exit(0 if not summary["failures"] else 1)
