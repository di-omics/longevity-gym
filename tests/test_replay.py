import json

import pytest

from longevityrl.cli import main
from longevityrl.replay import run_replay


def test_policies_share_a_start_and_each_spend_the_same_budget():
    report = run_replay(seed=17, rounds=3, batch_size=6, warm_start=8)
    assert set(report["policies"]) == {"random", "fixed", "greedy", "active", "planner"}
    initial = set(report["warm_ids"])
    assert len(initial) == 8
    known = dict(zip(report["warm_ids"], report["warm_observed"], strict=True))
    for rounds in report["policies"].values():
        assert len(rounds) == 3
        seen = initial.copy()
        hits = 0
        for index, row in enumerate(rounds, start=1):
            selected = set(row["selected"])
            assert row["round"] == index
            assert len(selected) == len(row["selected"]) == 6
            assert seen.isdisjoint(selected)
            seen.update(selected)
            for item, observation in zip(row["selected"], row["observed"], strict=True):
                assert observation in (0, 1, 2, 3)
                assert known.setdefault(item, observation) == observation
            assert row["joint_hits"] == row["observed"].count(3)
            hits += row["joint_hits"]
            assert row["cumulative_hits"] == hits


def test_replay_cli_is_reproducible_and_emits_valid_json(capsys):
    args = ["replay", "--seed", "13", "--rounds", "2", "--batch-size", "5"]
    main([*args, "--json"])
    expected = json.loads(capsys.readouterr().out)
    assert expected == run_replay(seed=13, rounds=2, batch_size=5)
    main(args)
    summary = capsys.readouterr().out
    assert "round 2" in summary
    for policy, rounds in expected["policies"].items():
        assert policy + "\t" + "\t".join(str(r["cumulative_hits"]) for r in rounds) in summary


def test_entire_pool_can_be_used_without_resampling():
    report = run_replay(rounds=5, batch_size=300, warm_start=36)
    for rounds in report["policies"].values():
        used = report["warm_ids"] + [item for row in rounds for item in row["selected"]]
        assert len(set(used)) == len(used) == 1536
    assert len({rows[-1]["cumulative_hits"] for rows in report["policies"].values()}) == 1


def test_multi_campaign_cli_reports_paired_outcomes(capsys):
    main(["replay", "--seed", "5", "--campaigns", "3", "--json"])
    summary = json.loads(capsys.readouterr().out)
    traces = [run_replay(seed=seed)["policies"] for seed in range(5, 8)]
    for policy, average in summary["mean_hits"].items():
        assert average == pytest.approx(sum(t[policy][-1]["cumulative_hits"] for t in traces) / 3)
    for policy in ("greedy", "active"):
        delta = [t["planner"][-1]["cumulative_hits"] - t[policy][-1]["cumulative_hits"] for t in traces]
        paired = summary["planner_comparisons"][policy]
        assert paired["wins"] == sum(x > 0 for x in delta)
        assert paired["ties"] == delta.count(0)
        assert paired["losses"] == sum(x < 0 for x in delta)
        assert paired["mean_difference"] == pytest.approx(sum(delta) / 3)


@pytest.mark.parametrize("options", [
    {"seed": -1}, {"batch_size": 337}, {"batch_size": 0},
    {"rounds": 0}, {"rounds": 5, "batch_size": 336},
])
def test_out_of_budget_settings_fail_before_the_comparison(options):
    with pytest.raises(ValueError):
        run_replay(**options)
