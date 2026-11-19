"""Scripted policies: one reference analysis, twelve named mistakes that each change one thing, two constants.

The reference is a first draft and a floor, not an optimum:
  0. 30 per arm with placebo, 26 weeks, follow-up plates randomized, covariates measured;
  1. placebo-controlled change scores, with the follow-up plate as a term in the model;
  2. use each clock's calibration card: subtract what the measured shifts in cell mix and
     inflammation explain, then divide by the clock's slope (years of reading per year of aging);
  3. take the median within each modality (six proteomic clocks, two methylation clocks);
  4. believe the more conservative modality, and report zero when the two disagree in sign;
  5. report exactly zero when the result is under 0.2 years.
Rule 4 is the only defence against something the cards do not describe, such as a clock family
that reads disease activity as age.
"""
from __future__ import annotations

import numpy as np

from .clocks import CLOCK_NAMES, EPIGENETIC, PROTEOMIC, clocks
from .interventions import GEROPROTECTIVE_THRESHOLD

REFERENCE_DESIGN = {"n_per_arm": 30, "placebo": True, "weeks": 26, "plate_layout": "randomized",
                    "measure_covariates": True, "clocks": list(CLOCK_NAMES)}
ZERO_BAND = 0.2   # years; a smaller estimate is reported as exactly zero
COVARIATES = {"lymphoid_z": "years_per_sd_cell_mix", "crp_z": "years_per_sd_inflammation"}


def _end_changes(rows, key):
    base = {r["id"]: r for r in rows if r["timepoint"] == "baseline"}
    return [(r["arm"] == "treated", r[key] - base[r["id"]][key], r["plate"])
            for r in rows if r["timepoint"] == "end"]


def clock_effect(rows, clock, weeks, use_plate=True) -> float:
    """Treated-minus-placebo change for one clock, in years of clock reading. The follow-up plate
    enters the model when it is not confounded with the arm. Without a placebo arm: the mean
    change in the treated minus the calendar time that passed."""
    ch = _end_changes(rows, clock)
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


def covariate_shift(rows, name) -> float:
    """Treated-minus-placebo mean change of a covariate (the treated mean change when there is no
    placebo arm). Zero when the covariate was not measured."""
    if name not in rows[0]:
        return 0.0
    ch = _end_changes(rows, name)
    treated = [c[1] for c in ch if c[0]]
    placebo = [c[1] for c in ch if not c[0]]
    return float(np.mean(treated) - (np.mean(placebo) if placebo else 0.0))


def calibrated_effects(spec, obs, names, use_plate=True, use_cards=True) -> dict:
    """Each clock's effect in years of organ aging: raw change, minus what the measured covariate
    shifts explain, divided by the clock's slope. With use_cards=False: the raw clock change."""
    rows, weeks = obs["rows"], obs["weeks"]
    shifts = {key: covariate_shift(rows, cov) for cov, key in COVARIATES.items()}
    out = {}
    for name in names:
        x = clock_effect(rows, name, weeks, use_plate)
        if use_cards:
            card = spec["clocks"][name]["calibration"]
            x = (x - sum(card[key] * shift for key, shift in shifts.items())) / card["years_per_year_of_aging"]
        out[name] = x
    return out


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
    e = 0.0 if abs(e) < ZERO_BAND else e
    return {"effect_years": e, "geroprotective": bool(e <= GEROPROTECTIVE_THRESHOLD)}


def make_policy(design_changes=None, analysis="reference"):
    design = {**REFERENCE_DESIGN, **(design_changes or {})}

    def policy(spec, obs=None):
        if obs is None:
            return {**design, "clocks": list(design["clocks"])}
        per = calibrated_effects(spec, obs, design["clocks"], use_plate=analysis != "ignore_plate",
                                 use_cards=analysis != "raw_changes")
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
    "no_covariates": make_policy({"measure_covariates": False}),
    "raw_clock_changes": make_policy(analysis="raw_changes"),
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
    "no_covariates": "do not measure cell mix and inflammation, so known leaks stay in",
    "raw_clock_changes": "ignore the calibration cards: read raw clock changes as years of aging",
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
