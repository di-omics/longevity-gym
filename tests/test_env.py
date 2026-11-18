import json
import math
import pathlib
import subprocess
import sys

import numpy as np
import pytest

from longevitygym import make
from longevitygym.clocks import CLOCK_NAMES, EPIGENETIC, PROTEOMIC, clock_cards, clock_table, clocks
from longevitygym.biology import KIND_SHARED, PANEL
from longevitygym.interventions import INTERVENTIONS, POTENCY_RANGE
from longevitygym.policies import POLICIES, REFERENCE_DESIGN, clock_effect, run_episode

ROOT = pathlib.Path(__file__).resolve().parents[1]
REAL_NAMES = ("ProtAge", "OrganAge", "PAC", "P3GPT", "PAOPAC", "Insilico", "rentosertib")


def _trial(intervention, cohort, seeds=(3, 4, 5, 6), dose=2, n=150):
    """Mean clock readings over a few large simulated trials at nominal potency, and the truth."""
    per = {c: [] for c in CLOCK_NAMES}
    for seed in seeds:
        env = make(seed=seed, intervention=intervention, cohort=cohort, dose=dose, potency=(1.0, 1.0))
        env.reset()
        obs, *_ = env.step({**REFERENCE_DESIGN, "n_per_arm": n})
        for c in CLOCK_NAMES:
            per[c].append(clock_effect(obs["rows"], c, 26))
    return {c: float(np.mean(v)) for c, v in per.items()}, env.truth()["true_effect_years"]


# ---------------------------------------------------------------- clocks
def test_eight_clocks_six_proteomic_two_methylation():
    assert len(CLOCK_NAMES) == 8 and len(PROTEOMIC) == 6 and len(EPIGENETIC) == 2
    targets = [clocks()[c].target for c in PROTEOMIC]
    assert targets.count("chronological") == 4 and targets.count("mortality") == 2


def test_clocks_track_their_targets_on_held_out_people():
    for row in clock_table():
        assert row["r"] > 0.85, row["clock"]
        assert 0.6 < row["per_year_organ_aging"] < 1.3, row["clock"]


def test_every_proteomic_clock_uses_a_shared_protein_and_reads_fibrosis_as_age():
    shared = set(np.flatnonzero(PANEL.prot_kind == KIND_SHARED))
    table = {r["clock"]: r for r in clock_table()}
    for name in PROTEOMIC:
        assert shared & set(clocks()[name].features), name
        assert table[name]["per_unit_fibrosis"] > 0.1, name
    for name in EPIGENETIC:
        assert abs(table[name]["per_unit_fibrosis"]) < 0.05, name


def test_whole_panel_clocks_discount_fibrosis_because_a_few_training_people_had_it():
    from longevitygym.clocks import train_clocks
    shipped = {r["clock"]: r["per_unit_fibrosis"] for r in clock_table()}
    healthy = {r["clock"]: r["per_unit_fibrosis"] for r in clock_table(train_clocks(population="none"))}
    for name in ("prot_dense_chrono", "prot_dense_chrono_b"):
        assert healthy[name] > 1.7 * shipped[name], name
        assert shipped[name] < min(shipped[c] for c in PROTEOMIC if "dense" not in c), name


def test_mortality_clocks_read_inflammation_and_chronological_ones_do_not():
    table = {r["clock"]: r for r in clock_table()}
    for name in PROTEOMIC:
        reads = table[name]["per_sd_inflammation"]
        assert (reads > 1.0) if clocks()[name].target == "mortality" else (abs(reads) < 0.3), name


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
                                {"potency": 1.0}, {"potency": (0.0, 1.0)}])
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


# ---------------------------------------------------------------- the built-in lessons
def test_antifibrotic_moves_every_proteomic_clock_but_not_the_organs():
    est, truth = _trial("antifibrotic", "fibrosis")
    assert -0.2 < truth < 0
    for name in PROTEOMIC:
        assert est[name] < truth - 0.05, name
    assert np.median([est[n] for n in PROTEOMIC]) < -0.5      # a proteomics-only reading calls it geroprotective
    for name in EPIGENETIC:
        assert abs(est[name] - truth) < 0.3, name
    healthy, truth_h = _trial("antifibrotic", "healthy")
    assert truth_h == 0.0 and max(abs(v) for v in healthy.values()) < 0.3


def test_methylation_clocks_overread_reprogramming_and_proteomic_ones_do_not():
    est, truth = _trial("reprogramming_like", "healthy")
    for name in EPIGENETIC:
        assert est[name] < truth - 3, name
    for name in PROTEOMIC:
        assert abs(est[name] - truth) < 0.4, name


def test_cell_mix_shift_moves_only_the_chronological_methylation_clock():
    est, truth = _trial("immune_mobilizer", "healthy")
    assert truth == 0.0 and est["epi_chrono"] < -0.8
    for name in PROTEOMIC:
        assert abs(est[name]) < 0.3, name


def test_reference_beats_the_named_mistakes_on_average():
    seeds = range(60)
    mean = lambda p: float(np.mean([run_episode(make(seed=s), POLICIES[p])[0] for s in seeds]))
    reference = mean("reference")
    assert reference > 0.75
    for p in ("always_no", "always_yes", "no_placebo", "plates_by_arm", "cherry_pick_best_clock", "short_trial_4wk"):
        assert reference - mean(p) > 0.1, p


# ---------------------------------------------------------------- repo hygiene
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
