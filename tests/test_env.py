import pathlib

import numpy as np
import pytest

from longevitygym import make
from longevitygym.clocks import CLOCK_NAMES, PROTEOMIC, clock_table
from longevitygym.interventions import INTERVENTIONS
from longevitygym.policies import POLICIES, clock_effect, run_episode

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_eight_clocks_six_proteomic_and_accurate():
    assert len(CLOCK_NAMES) == 8 and len(PROTEOMIC) == 6
    for row in clock_table():
        assert row["r"] > 0.9


def test_deterministic():
    a = run_episode(make(seed=5), POLICIES["expert"])
    b = run_episode(make(seed=5), POLICIES["expert"])
    assert a[0] == b[0] and a[1]["estimate"] == b[1]["estimate"]


def test_truth_hidden_until_report():
    env = make(seed=1)
    spec = env.reset()
    obs, reward, done, info = env.step(POLICIES["expert"](spec))
    text = repr(spec) + repr(obs) + repr(info)
    assert not done and reward == 0.0
    for name in INTERVENTIONS:
        assert name not in text
    assert "true_effect" not in text


def test_inert_reads_zero_and_antifibrotic_only_acts_in_disease():
    assert INTERVENTIONS["inert"].true_effect(3, "healthy") == 0.0
    assert INTERVENTIONS["antifibrotic"].true_effect(2, "healthy") == 0.0
    assert INTERVENTIONS["antifibrotic"].true_effect(2, "fibrosis") < 0


def _effect(intervention, cohort, clock, seed=3):
    env = make(seed=seed, intervention=intervention, cohort=cohort, dose=2)
    spec = env.reset()
    obs, *_ = env.step({**POLICIES["expert"](spec), "n_per_arm": 150})
    return clock_effect(obs["rows"], clock, 26, adjust=False), env.truth()["true_effect_years"]


def test_disease_trained_clock_overreads_a_disease_treatment():
    est, truth = _effect("antifibrotic", "fibrosis", "fibrosis_chrono")
    assert est < truth - 0.5


def test_methylation_clock_overreads_reprogramming():
    est, truth = _effect("reprogramming_like", "healthy", "epi_chrono")
    assert est < truth - 3


def test_mortality_clock_reads_inflammation_as_age():
    est, truth = _effect("anti_inflammatory", "healthy", "organ_mortality")
    assert truth == 0.0 and est < -0.5


def test_expert_beats_null_and_named_mistakes_on_average():
    seeds = range(40)
    mean = lambda p: np.mean([run_episode(make(seed=s), POLICIES[p])[0] for s in seeds])
    expert = mean("expert")
    assert expert > 0.7
    for p in ("null", "no_placebo", "batch_by_arm", "cherry_pick_best_clock", "trust_disease_clock", "short_trial_4wk"):
        assert expert - mean(p) > 0.1, p


def test_bad_actions_rejected():
    env = make(seed=0); env.reset()
    with pytest.raises(ValueError):
        env.step({"n_per_arm": 3})
    with pytest.raises(ValueError):
        env.step({"clocks": ["horvath"]})


def test_repo_is_ascii():
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".md", ".toml", ".json"} and ".venv" not in path.parts:
            path.read_text().encode("ascii")
