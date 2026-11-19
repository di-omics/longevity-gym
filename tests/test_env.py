"""env.py: what the agent sees, and that one env object is one episode."""
import json
import math

import numpy as np
import pytest

from longevitygym import make
from longevitygym.clocks import CLOCK_NAMES, clock_cards, clock_table
from longevitygym.interventions import INTERVENTIONS, POTENCY_RANGE
from longevitygym.policies import POLICIES, run_episode

REAL_NAMES = ("ProtAge", "OrganAge", "PAC", "P3GPT", "PAOPAC", "Insilico", "rentosertib")


# ---------------------------------------------------------------- what the agent sees
def test_task_never_names_a_real_clock_drug_or_company():
    env = make(seed=1)
    spec = env.reset()
    obs, *_ = env.step(POLICIES["reference"](spec))
    text = json.dumps(spec) + json.dumps(obs)
    for word in REAL_NAMES:
        assert word.lower() not in text.lower(), word


def test_truth_hidden_until_report():
    env = make(seed=1)
    spec = env.reset()
    obs, reward, done, info = env.step(POLICIES["reference"](spec))
    text = json.dumps(spec) + json.dumps(obs) + json.dumps(info)
    assert not done and reward == 0.0
    for name in INTERVENTIONS:
        assert name not in text
    assert "true_effect" not in text and "potency" not in text


def test_deterministic_and_forced_arguments_do_not_shift_the_task():
    a = run_episode(make(seed=5), POLICIES["reference"])
    b = run_episode(make(seed=5), POLICIES["reference"])
    assert a[0] == b[0] and a[1]["estimate"] == b[1]["estimate"]
    free, forced = make(seed=5), make(seed=5, dose=2)
    assert (free.code, free.cohort, free.intervention.name, free.potency) == \
           (forced.code, forced.cohort, forced.intervention.name, forced.potency)


def test_truth_is_continuous_not_a_short_list():
    truths = {round(make(seed=s).truth()["true_effect_years"], 6) for s in range(300)}
    assert len(truths) > 120
    for s in range(50):
        assert all(POTENCY_RANGE[0] <= q <= POTENCY_RANGE[1] for q in make(seed=s).potency)


def test_spec_carries_a_calibration_card_for_every_clock_but_not_its_fibrosis_reading():
    spec = make(seed=2).reset()
    table = {r["clock"]: r for r in clock_table()}
    for name in CLOCK_NAMES:
        card = spec["clocks"][name]["calibration"]
        assert card == clock_cards()[name]
        assert card["years_per_year_of_aging"] == round(table[name]["per_year_organ_aging"], 2)
        assert not any("fibrosis" in key for key in card)
    spec["design_defaults"]["clocks"].clear()                       # editing a task must not leak into later envs
    assert len(make(seed=3).reset()["design_defaults"]["clocks"]) == 8


@pytest.mark.parametrize("kw", [{"seed": -1}, {"seed": 1.9}, {"seed": True}, {"dose": 4}, {"dose": 0},
                                {"cohort": "ipf"}, {"intervention": "aspirin"}, {"potency": (1.0, float("inf"))},
                                {"potency": 1.0}, {"potency": (0.0, 1.0)}, {"noise": "loud"}])
def test_bad_constructor_arguments_rejected(kw):
    with pytest.raises(ValueError):
        make(**{"seed": 0, **kw})


# ---------------------------------------------------------------- one env object is one episode
def test_reset_cannot_replay_a_task_and_a_second_design_is_refused():
    env = make(seed=0)
    spec = env.reset()
    env.reset()                                   # harmless before anything has run
    env.step({"n_per_arm": 150})
    with pytest.raises(RuntimeError):
        env.reset()                               # no free look at a big trial
    with pytest.raises(ValueError):
        env.step({"n_per_arm": 8, "placebo": False})
    _, reward, done, info = env.step({"effect_years": 0.0, "geroprotective": False})
    assert done and info["cost"] == pytest.approx(300 * 0.05 / 120)
    with pytest.raises(RuntimeError):
        env.reset()                               # no second episode with the answer in hand
    with pytest.raises(RuntimeError):
        env.step({"effect_years": 0.0, "geroprotective": False})


@pytest.mark.parametrize("design", [
    {"n_per_arm": 3}, {"n_per_arm": 12.9}, {"n_per_arm": True}, {"weeks": 5}, {"placebo": "false"},
    {"measure_covariates": 1}, {"clocks": ["horvath"]}, {"clocks": []}, {"clocks": ["epi_chrono", "epi_chrono"]},
    {"n_per_arms": 150}, {"plate_layout": "by_site"}, {"effect_years": 0.0, "geroprotective": False}, "design", None,
    {"clocks": [["epi_chrono"]]}, {"clocks": ["epi_chrono", {}]}, {1: 2, "a": 3}, {"plate_layout": np.array(["by_arm"])},
])
def test_bad_designs_rejected(design):
    env = make(seed=0)
    env.reset()
    with pytest.raises(ValueError):
        env.step(design)


@pytest.mark.parametrize("report", [
    {"effect_years": float("nan"), "geroprotective": False}, {"effect_years": float("inf"), "geroprotective": False},
    {"effect_years": "0.1", "geroprotective": False}, {"effect_years": 0.0, "geroprotective": "false"},
    {"effect_years": -2.0, "geroprotective": False}, {"effect_years": 0.0, "geroprotective": True},
    {"effect_years": 0.0}, {"effect_years": 0.0, "geroprotective": False, "note": "x"}, {"n_per_arm": 8}, None,
    {"effect_years": 10 ** 400, "geroprotective": False},
])
def test_bad_reports_rejected_without_ending_the_episode(report):
    env = make(seed=0)
    env.reset()
    env.step({})
    with pytest.raises(ValueError):
        env.step(report)
    _, reward, done, _ = env.step({"effect_years": 0.0, "geroprotective": False})
    assert done and math.isfinite(reward)


def test_designs_are_compared_on_the_same_people_and_noise():
    def rows(**design):
        env = make(seed=7)
        obs, *_ = env.step(design)
        return {(r["id"], r["timepoint"]): r for r in obs["rows"]}
    full = rows(n_per_arm=60)
    assert len(full) == 240
    for key, row in rows(n_per_arm=12).items():                   # size: both visits
        assert row == full[key]
    for key, row in rows(n_per_arm=60, placebo=False).items():    # placebo: the treated arm is untouched
        assert row == full[key]
    by_arm, short = rows(n_per_arm=60, plate_layout="by_arm"), rows(n_per_arm=60, weeks=4)
    same_plate = 0
    for key, row in full.items():
        if key[1] == "baseline":                                  # layout and duration: same baseline sample
            assert row == by_arm[key] == short[key]
        elif row["plate"] == by_arm[key]["plate"]:                # layout: same follow-up noise on the same plate
            assert row == by_arm[key]
            same_plate += 1
    assert same_plate > 30
