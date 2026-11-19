"""Held-out evaluation, equal trial budgets, and the Longevity RL CLI."""
import json

import numpy as np
import pytest

from longevityrl import ClockTrialEnv, make
from longevityrl.benchmark import run_benchmark
from longevityrl.cli import main
from longevityrl.policies import POLICIES, REFERENCE_DESIGN


@pytest.mark.parametrize("noise", ["default", "calibrated"])
def test_scores_match_existing_policies_on_identical_trials(noise):
    result = run_benchmark(train_seeds=4, test_seeds=3, seed=99, noise=noise)
    assert result["name"] == "Longevity RL"
    assert result["train_seeds"] == [99, 100, 101, 102]
    assert result["test_seeds"] == [103, 104, 105]
    assert result["design"] == REFERENCE_DESIGN
    assert [row["seed"] for row in result["episodes"]] == result["test_seeds"]
    assert set(result["policies"]) == {"reference", "always_no", "average_all_clocks", "model_based"}

    for row in result["episodes"]:
        for name in ("reference", "always_no", "average_all_clocks"):
            env = make(seed=row["seed"], noise=noise)
            spec = env.reset()
            obs, *_ = env.step(REFERENCE_DESIGN)
            _, reward, done, info = env.step(POLICIES[name](spec, obs))
            assert done and row["cost"] == info["cost"]
            assert row["true_effect_years"] == info["true_effect_years"]
            assert row["policies"][name]["estimate"] == info["estimate"]
            assert row["policies"][name]["reward"] == pytest.approx(reward)

    reference = np.array([row["policies"]["reference"]["reward"] for row in result["episodes"]])
    for name, metrics in result["policies"].items():
        rows = [row["policies"][name] for row in result["episodes"]]
        reward = np.array([row["reward"] for row in rows])
        differences = reward - reference
        assert metrics["mean_reward"] == pytest.approx(reward.mean())
        assert metrics["mean_abs_error_years"] == pytest.approx(np.mean([r["abs_error"] for r in rows]))
        assert metrics["call_accuracy"] == pytest.approx(np.mean([r["call_correct"] for r in rows]))
        assert metrics["mean_paired_reward_vs_reference"] == pytest.approx(differences.mean())
        assert metrics["paired_reward_se"] == pytest.approx(differences.std(ddof=1) / np.sqrt(len(rows)))


def test_changing_hidden_test_answers_changes_scores_but_not_decisions(monkeypatch):
    before = run_benchmark(train_seeds=4, test_seeds=2)
    held_out = set(before["test_seeds"])
    assert held_out.isdisjoint(before["train_seeds"])
    original_truth = ClockTrialEnv.truth

    def altered_truth(env):
        truth = original_truth(env)
        if env.seed in held_out:
            truth.update(true_effect_years=50.0, geroprotective=False)
        return truth

    monkeypatch.setattr(ClockTrialEnv, "truth", altered_truth)
    after = run_benchmark(train_seeds=4, test_seeds=2)
    for first, second in zip(before["episodes"], after["episodes"], strict=True):
        assert first["true_effect_years"] != second["true_effect_years"]
        for name in first["policies"]:
            decision = first["policies"][name]
            rescored = second["policies"][name]
            assert (decision["estimate"], decision["call"]) == (rescored["estimate"], rescored["call"])
            assert decision["abs_error"] != rescored["abs_error"]


def test_cli_json_reproduces_python_report(capsys):
    main(["benchmark", "--train-seeds", "4", "--test-seeds", "2", "--json"])
    assert json.loads(capsys.readouterr().out) == run_benchmark(train_seeds=4, test_seeds=2)


def test_one_test_seed_has_no_standard_error():
    result = run_benchmark(train_seeds=1, test_seeds=1)
    assert all(row["paired_reward_se"] is None for row in result["policies"].values())
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("invalid", [
    {"train_seeds": False}, {"test_seeds": 0}, {"seed": -1}, {"noise": "unknown"},
])
def test_invalid_settings(invalid):
    with pytest.raises(ValueError):
        run_benchmark(**invalid)
