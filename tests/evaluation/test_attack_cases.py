from __future__ import annotations

import json
from pathlib import Path

import pytest

from fin_assistant.evaluation import GoldCase, score_batch


FIXTURE = Path(__file__).parents[2] / "evaluation" / "fixtures" / "attack_cases.json"


@pytest.mark.parametrize("attack", json.loads(FIXTURE.read_text(encoding="utf-8"))["attacks"])
def test_attack_never_receives_perfect_behavior_score(attack):
    gold = [GoldCase.from_dict(case) for case in attack["gold"]]
    report = score_batch(gold, attack["predictions"])

    assert report.behavior_correct_count < report.n, attack["name"]
    assert any(case.errors for case in report.cases), attack["name"]


def test_always_clarify_attack_has_zero_answer_rate_and_asks_unnecessarily():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    attack = next(item for item in payload["attacks"] if item["name"] == "always_clarify")
    report = score_batch(
        [GoldCase.from_dict(case) for case in attack["gold"]], attack["predictions"]
    ).to_dict()

    assert report["answer_rate_A_over_N"] == 0.0
    assert report["unnecessary_clarification_count"] == 1
