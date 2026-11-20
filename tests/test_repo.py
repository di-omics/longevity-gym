"""The repo's own rules: aggregates only, ASCII only, README built from results/."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_repo_holds_no_participant_level_real_data():
    from longevityrl import realcheck
    assert realcheck.REAL["n_samples"] == 168
    numbers = json.dumps(realcheck.REAL)
    assert len(numbers) < 3000                                                # aggregates only
    assert not list(ROOT.rglob("*.xlsx")) or all(".venv" in str(p) or "venv" in p.parts for p in ROOT.rglob("*.xlsx"))


def _tracked_files():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        files = [ROOT / line for line in out.splitlines() if line]
        if files:
            return files
    except (OSError, subprocess.CalledProcessError):
        pass
    files = [ROOT / "README.md", ROOT / "pyproject.toml", ROOT / ".gitignore"]
    for folder in ("src", "tests", "docs", "results", "tools", ".github"):
        files += [p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    return files


def test_repo_is_ascii_with_no_em_dashes():
    for path in _tracked_files():
        if path.exists() and path.suffix != ".pyc":
            data = path.read_bytes()
            assert all(b < 128 for b in data), path


def test_readme_is_built_from_the_results_files():
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "build_readme.py"), "--check"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


def _builder():
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_readme", ROOT / "tools" / "build_readme.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sign_test_by_enumeration(wins, losses):
    # Two-sided: every split of the differing campaigns at least as far from even as the one seen.
    from fractions import Fraction
    from math import comb
    n = wins + losses
    if n == 0:
        return 1.0
    far = abs(2 * wins - n)
    total = sum(Fraction(comb(n, k), 2 ** n) for k in range(n + 1) if abs(2 * k - n) >= far)
    return float(min(Fraction(1), total))


def test_sign_test_matches_an_independent_count():
    b = _builder()
    assert b.sign_test(0, 10) == 2 / 1024
    assert b.sign_test(5, 5) == 1.0
    assert b.sign_test(0, 0) == 1.0
    for wins, losses in ((0, 10), (5, 5), (26, 34), (0, 0), (1, 0), (66, 32), (7, 3), (40, 59)):
        expected = _sign_test_by_enumeration(wins, losses)
        assert abs(b.sign_test(wins, losses) - expected) < 1e-12, (wins, losses)
        assert b.sign_test(wins, losses) == b.sign_test(losses, wins)
    assert 0.36 < b.sign_test(26, 34) < 0.37


def test_p_values_are_written_without_exponents():
    b = _builder()
    cases = {1.0: "1.00", 0.37: "0.37", 0.05: "0.05", 0.01: "0.01", 0.0099: "0.01", 0.0008: "0.0008",
             0.00083: "0.0008", 0.0034: "0.003", 0.0001: "0.0001", 0.00009: "below 0.0001",
             1e-12: "below 0.0001"}
    for p, text in cases.items():
        assert b.format_p(p) == text, p
        assert "e" not in b.format_p(p).replace("below", "")


def _replay(wins, ties, losses, extra=None):
    means = {"random": 20.0, "fixed": 30.0, "active": 31.0, "planner": 40.0, "greedy": 39.5}
    means.update(extra or {})
    return {"first_seed": 3, "campaigns": wins + ties + losses, "rounds": 2, "batch_size": 5,
            "mean_hits": means,
            "planner_comparisons": {"greedy": {"wins": wins, "ties": ties, "losses": losses},
                                    "active": {"wins": 9, "ties": 1, "losses": 0}}}


def test_replay_verdict_follows_the_sign_test():
    b = _builder()
    yes = b.replay_block(_replay(10, 2, 0))
    assert "So far the answer is yes: the planner finds more joint hits than the greedy baseline." in yes
    assert "wins 10 campaigns, ties 2 and loses 0" in yes and "on the 10 campaigns that differ" in yes
    assert "seeds 3 to 14" in yes and "10 new candidates per policy per campaign" in yes
    fewer = b.replay_block(_replay(0, 2, 10))
    assert "So far the answer is no: the planner finds fewer joint hits than the greedy baseline." in fewer
    for w, l in ((5, 5), (6, 4), (4, 6), (0, 0)):
        text = " ".join(b.replay_block(_replay(w, 2, l)).split())
        assert ("So far the answer is no: the planner does not find more joint hits than the greedy "
                "baseline, and the 2 are not distinguishable in these campaigns.") in text, (w, l)
    rows = [line for line in yes.splitlines() if line.startswith("| ") and "Policy" not in line]
    assert rows[0] == "| planner (two-round lookahead) | 40.00 |"
    assert rows[-1] == "| random (random selection) | 20.00 |"


def test_generated_prose_never_splits_a_hyphenated_word():
    b = _builder()
    texts = [b.replay_block(_replay(w, 2, l)) for w in range(12) for l in range(12)]
    texts += [b.benchmark_block(_benchmark(d, s)) for d in (-0.3, 0.0, 0.3) for s in (0.05, 0.11)]
    for text in texts:
        prose = [line for line in text.splitlines() if line and not line.startswith("|")]
        assert not any(line.endswith("-") for line in prose), text


def _benchmark(d, s, extra=None):
    names = ["reference", "always_no", "model_based"] + list(extra or [])
    policies = {name: {"mean_reward": 0.5, "call_accuracy": 0.5, "mean_abs_error_years": 0.25,
                       "mean_paired_reward_vs_reference": 0.0, "paired_reward_se": 0.0} for name in names}
    policies["model_based"].update(mean_reward=0.5 + d, mean_paired_reward_vs_reference=d, paired_reward_se=s)
    episodes = [{"policies": {name: {"call_correct": (i < 2 or name != "always_no")} for name in names}}
                for i in range(3)]
    return {"train_seeds": [0, 1, 2, 3], "test_seeds": [4, 5, 6], "noise": "default",
            "policies": policies, "episodes": episodes}


def _verdict(d, s, b=None):
    b = b or _builder()
    return " ".join(b.benchmark_block(_benchmark(d, s)).split("\n\n")[-1].split())


def test_benchmark_verdict_uses_the_bar_of_the_qc_card():
    b = _builder()
    bar = b.SE_BAR
    assert bar == 3
    assert b.judged(bar * 0.25, 0.25, "win", "lose", "tie") == "win"     # the QC card's own verdicts
    assert b.judged(-bar * 0.25, 0.25, "win", "lose", "tie") == "lose"
    below = ("The model-based policy scores below the scripted reference: mean reward 0.200 against 0.500, "
             "a paired difference of -0.300 (SE 0.098) over 3 test trials.")
    assert _verdict(-0.3, 0.098) == below                                  # 3.06 SE: just outside the bar
    assert _verdict(0.3, 0.098) == ("The model-based policy scores above the scripted reference: mean reward "
                                    "0.800 against 0.500, a paired difference of +0.300 (SE 0.098) over 3 "
                                    "test trials.")
    assert _verdict(-0.3, 0.102) == (                                      # 2.94 SE: just inside the bar
        "The model-based policy does not beat the scripted reference. Its mean reward is lower, 0.200 against "
        "0.500, but the paired difference of -0.300 (SE 0.102) over 3 test trials is 2.9 standard errors, under "
        "the bar of 3 that the QC card below uses to say one policy scores lower than another.")
    assert _verdict(0.3, 0.102) == (
        "The model-based policy is ahead of the scripted reference on mean reward, 0.800 against 0.500, but the "
        "paired difference of +0.300 (SE 0.102) over 3 test trials is 2.9 standard errors, under the bar of 3 "
        "that the QC card below uses to say one policy scores lower than another.")
    # 2.97 SE would round to 3.0 with 1 decimal, and "3.0 ..., under the bar of 3" reads as a contradiction.
    assert "is just under 3 standard errors, under the bar of 3" in _verdict(-0.3, 0.101)
    assert _verdict(0.0, 0.05) == ("The model-based policy and the scripted reference have the same mean "
                                   "reward, 0.500, over 3 test trials.")
    # Exactly at the bar (0.75 and 0.25 are exact in binary): the same side as judged() takes.
    for d, side in ((-0.75, "lose"), (0.75, "win")):
        assert b.judged(d, 0.25, "win", "lose", "tie") == side
        word = "below" if side == "lose" else "above"
        assert _verdict(d, 0.25).startswith(f"The model-based policy scores {word} the scripted reference:"), d
    # The bar in the sentence is the constant, not a second copy of the number.
    b.SE_BAR = 4
    assert "under the bar of 4 that the QC card below" in _verdict(-0.3, 0.102, b)
    assert _verdict(-0.75, 0.25, b).startswith("The model-based policy does not beat")
    text = " ".join(b.benchmark_block(_benchmark(-0.3, 0.102)).split())
    assert "seeds 0 to 3" in text and "seeds 4 to 6" in text and "default noise profile" in text
    rows = {line.split(" | ")[0]: line for line in b.benchmark_block(_benchmark(-0.2, 0.05)).splitlines()
            if line.startswith("| ")}
    assert rows["| always_no (constant negative call)"].endswith("| 0.500 | 2 of 3 | 0.250 | +0.000 (SE 0.000) |")
    assert rows["| reference (scripted reference)"].endswith("| 3 of 3 | 0.250 |  |")


def test_the_qc_card_named_in_the_benchmark_verdict_comes_later_in_the_readme():
    text = (ROOT / "README.md").read_text()
    assert text.index("## Aging-clock benchmark") < text.index("the QC card below") < text.index("## Environment QC")
    assert "| read the QC card | [envqc.py](src/longevityrl/envqc.py), [results/qc_clock_trial.md]" in text
    assert "Verdicts: punished = the policy scores lower than the reference by at least 3 standard errors" in text


def test_a_zero_or_missing_standard_error_stops_the_build(tmp_path, monkeypatch):
    import pytest
    b = _builder()
    monkeypatch.setattr(b, "RES", tmp_path)
    for se in (0.0, None):
        (tmp_path / "benchmark.json").write_text(json.dumps(_benchmark(-0.2, se)))
        with pytest.raises(SystemExit, match="lacks a field the README needs"):
            b.load_result("benchmark.json", b.benchmark_block)
    data = _benchmark(-0.2, 0.05)
    del data["policies"]["model_based"]["paired_reward_se"]
    (tmp_path / "benchmark.json").write_text(json.dumps(data))
    with pytest.raises(SystemExit, match="lacks a field the README needs"):
        b.load_result("benchmark.json", b.benchmark_block)


def test_unknown_policy_names_are_shown_bare():
    b = _builder()
    replay = b.replay_block(_replay(5, 0, 5, {"mystery": 50.0}))
    assert "| mystery | 50.00 |" in replay.splitlines()
    bench = b.benchmark_block(_benchmark(0.0, 0.1, ["new_policy"]))
    assert any(line.startswith("| new_policy | 0.500 |") for line in bench.splitlines())


def test_missing_results_stop_the_build_with_a_clear_error(tmp_path, monkeypatch):
    import pytest
    b = _builder()
    monkeypatch.setattr(b, "RES", tmp_path)
    with pytest.raises(SystemExit, match="results/replay.json is missing"):
        b.load_result("replay.json", b.replay_block)
    data = _replay(5, 0, 5)
    del data["planner_comparisons"]["active"]
    (tmp_path / "replay.json").write_text(json.dumps(data))
    with pytest.raises(SystemExit, match="lacks a field the README needs"):
        b.load_result("replay.json", b.replay_block)
