"""Scripted policies: one reference analysis, ten named mistakes that each change one thing, two constants.

The reference is a first draft and a floor, not an optimum:
  0. 30 per arm with placebo, 26 weeks, follow-up plates randomized (30 is where this reward
     peaks under this analysis; see the enrolment curve on the QC card);
  1. placebo-controlled change scores, with the follow-up plate as a term in the model;
  2. the median effect within each modality (six proteomic clocks, two methylation clocks);
  3. believe the more conservative modality, and report zero when the two disagree in sign.
Rule 3 is the whole defence against a clock family that reads something other than aging. It
does not use the covariates, and it is known to miss a real effect when a cell-mix shift pushes
one methylation clock the other way (the mTOR-like archetype at its top dose).
"""
from __future__ import annotations

import numpy as np

from .clocks import CLOCK_NAMES, EPIGENETIC, PROTEOMIC, clocks
from .interventions import GEROPROTECTIVE_THRESHOLD

REFERENCE_DESIGN = {"n_per_arm": 30, "placebo": True, "weeks": 26, "plate_layout": "randomized",
                    "measure_covariates": False, "clocks": list(CLOCK_NAMES)}


def _changes(rows, clock):
    base = {r["id"]: r for r in rows if r["timepoint"] == "baseline"}
    return [(r["arm"] == "treated", r[clock] - base[r["id"]][clock], r["plate"])
            for r in rows if r["timepoint"] == "end"]


def clock_effect(rows, clock, weeks, use_plate=True) -> float:
    """Treated-minus-placebo change for one clock, in years. The follow-up plate enters the model
    when it is not confounded with the arm. Without a placebo arm: the mean change in the treated
    minus the calendar time that passed."""
    ch = _changes(rows, clock)
    arm = np.array([c[0] for c in ch], float)
    y = np.array([c[1] for c in ch])
    if arm.min() == 1.0:
        return float(y.mean() - weeks / 52)
    cols = [np.ones_like(y), arm]
    plate = np.array([c[2] == 2 for c in ch], float)
    if use_plate and 0 < plate.mean() < 1 and abs(np.corrcoef(arm, plate)[0, 1]) < 0.999:
        cols.append(plate)
    beta, *_ = np.linalg.lstsq(np.column_stack(cols), y, rcond=None)
    return float(beta[1])


def conservative_estimate(per_clock: dict) -> float:
    """Median per modality; the smaller one in size wins; zero if the modalities disagree in sign."""
    families = {}
    for name, v in per_clock.items():
        families.setdefault(clocks()[name].family, []).append(v)
    medians = [float(np.median(v)) for v in families.values()]
    if len(medians) == 1:
        return medians[0]
    if np.sign(medians[0]) != np.sign(medians[1]):
        return 0.0
    return min(medians, key=abs)


def report(effect: float) -> dict:
    e = round(float(effect), 3)
    return {"effect_years": e, "geroprotective": bool(e <= GEROPROTECTIVE_THRESHOLD)}


def make_policy(design_changes=None, analysis="reference"):
    design = {**REFERENCE_DESIGN, **(design_changes or {})}

    def policy(spec, obs=None):
        if obs is None:
            return dict(design)
        rows, weeks = obs["rows"], obs["weeks"]
        per = {c: clock_effect(rows, c, weeks, use_plate=analysis != "ignore_plate") for c in design["clocks"]}
        if analysis == "cherry_pick":
            return report(min(per.values()))
        if analysis == "pooled_mean":
            return report(float(np.mean(list(per.values()))))
        return report(conservative_estimate(per))
    return policy


def constant_policy(effect):
    def policy(spec, obs=None):
        if obs is None:
            return {"n_per_arm": 8, "placebo": False, "weeks": 4, "clocks": ["prot_dense_chrono"]}
        return report(effect)
    return policy


POLICIES = {
    "reference": make_policy(),
    "no_placebo": make_policy({"placebo": False}),
    "plates_by_arm": make_policy({"plate_layout": "by_arm"}),
    "ignore_plate": make_policy(analysis="ignore_plate"),
    "short_trial_4wk": make_policy({"weeks": 4}),
    "small_n_12": make_policy({"n_per_arm": 12}),
    "proteomics_only": make_policy({"clocks": list(PROTEOMIC)}),
    "epigenetics_only": make_policy({"clocks": list(EPIGENETIC)}),
    "one_clock": make_policy({"clocks": ["prot_dense_chrono"]}),
    "cherry_pick_best_clock": make_policy(analysis="cherry_pick"),
    "average_all_clocks": make_policy(analysis="pooled_mean"),
    "always_no": constant_policy(0.0),
    "always_yes": constant_policy(-1.2),
}
MISTAKES = {
    "no_placebo": "pre/post change in the treated arm only, minus calendar time",
    "plates_by_arm": "follow-up samples of each arm run on their own plate",
    "ignore_plate": "leave the follow-up plate out of the analysis",
    "short_trial_4wk": "stop at 4 weeks and report it as the 26-week effect",
    "small_n_12": "12 per arm instead of 30",
    "proteomics_only": "one modality: the six proteomic clocks agree, so trust them",
    "epigenetics_only": "one modality: the two methylation clocks only",
    "one_clock": "one clock: the whole-panel chronological proteomic clock only",
    "cherry_pick_best_clock": "report whichever clock shows the biggest reversal",
    "average_all_clocks": "average all eight clocks instead of checking that modalities agree",
    "always_no": "baseline: 8 people, ignore the data, always answer no effect",
    "always_yes": "baseline: 8 people, ignore the data, always answer 1.2 years younger",
}


def run_episode(env, policy) -> tuple[float, dict]:
    spec = env.reset()
    obs, _, _, _ = env.step(policy(spec))
    _, reward, done, info = env.step(policy(spec, obs))
    assert done
    return reward, info
