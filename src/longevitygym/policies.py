"""Scripted policies: one expert, one null, and named mistakes that each change ONE thing.

The expert's analysis is ordinary trial practice plus two aging-clock rules:
  1. never read a clock trained in the disease you are treating (it reads the disease);
  2. ask two independent modalities, and believe the more conservative one when they disagree.
"""
from __future__ import annotations

import numpy as np

from .clocks import CLOCK_NAMES, EPIGENETIC, PROTEOMIC, clocks
from .interventions import GEROPROTECTIVE_THRESHOLD

EXPERT_DESIGN = {"n_per_arm": 60, "placebo": True, "weeks": 26, "batch_layout": "randomized",
                 "measure_covariates": True, "clocks": list(CLOCK_NAMES)}


def _changes(rows, clock):
    base = {r["id"]: r for r in rows if r["timepoint"] == "baseline"}
    out = []
    for r in rows:
        if r["timepoint"] == "end":
            b = base[r["id"]]
            d = {"arm": r["arm"], "delta": r[clock] - b[clock]}
            for k in ("lymphoid_z", "crp_z"):
                if k in r:
                    d["d_" + k] = r[k] - b[k]
            out.append(d)
    return out


def clock_effect(rows, clock, weeks, adjust=True) -> float:
    """Treated-minus-placebo change for one clock; covariate-adjusted by regression when available.
    Without a placebo arm: mean change in the treated minus the calendar time that passed."""
    ch = _changes(rows, clock)
    y = np.array([c["delta"] for c in ch])
    arm = np.array([c["arm"] == "treated" for c in ch], float)
    if arm.min() == 1.0:  # no placebo
        return float(y.mean() - weeks / 52)
    cols = [np.ones_like(y), arm]
    if adjust and "d_lymphoid_z" in ch[0]:
        cols += [np.array([c["d_lymphoid_z"] for c in ch]), np.array([c["d_crp_z"] for c in ch])]
    beta, *_ = np.linalg.lstsq(np.column_stack(cols), y, rcond=None)
    return float(beta[1])


def usable_clocks(spec_cohort: str, chosen) -> list[str]:
    fib = "fibrotic" in spec_cohort
    return [c for c in chosen if not (fib and clocks()[c].trained_on == "fibrosis")]


def concordant_estimate(per_clock: dict) -> float:
    fams = {}
    for name, v in per_clock.items():
        fams.setdefault(clocks()[name].family, []).append(v)
    meds = [float(np.median(v)) for v in fams.values()]
    if len(meds) == 1:
        return meds[0]
    if np.sign(meds[0]) != np.sign(meds[1]):
        return 0.0
    return min(meds, key=abs)


def report(effect: float) -> dict:
    return {"effect_years": round(effect, 3), "geroprotective": bool(effect <= GEROPROTECTIVE_THRESHOLD)}


def make_policy(design_changes=None, analysis="expert"):
    design = {**EXPERT_DESIGN, **(design_changes or {})}

    def policy(spec, obs=None):
        if obs is None:
            return design
        rows, weeks = obs["rows"], obs["weeks"]
        chosen = design["clocks"]
        if analysis == "cherry_pick":
            per = {c: clock_effect(rows, c, weeks) for c in chosen}
            return report(min(per.values()))
        if analysis == "trust_disease_clock":
            return report(clock_effect(rows, "fibrosis_chrono", weeks))
        if analysis == "pooled_mean":
            per = {c: clock_effect(rows, c, weeks) for c in usable_clocks(spec["cohort"], chosen)}
            return report(float(np.mean(list(per.values()))))
        per = {c: clock_effect(rows, c, weeks) for c in usable_clocks(spec["cohort"], chosen)}
        return report(concordant_estimate(per))
    return policy


def null_policy(spec, obs=None):
    if obs is None:
        return {"n_per_arm": 8, "placebo": False, "weeks": 4, "measure_covariates": False, "clocks": ["prot_chrono"]}
    return report(0.0)


def always_yes_policy(spec, obs=None):
    if obs is None:
        return {"n_per_arm": 8, "placebo": False, "weeks": 4, "measure_covariates": False, "clocks": ["prot_chrono"]}
    return {"effect_years": -1.2, "geroprotective": True}


POLICIES = {
    "expert": make_policy(),
    "no_placebo": make_policy({"placebo": False}),
    "batch_by_arm": make_policy({"batch_layout": "by_arm"}),
    "no_covariates": make_policy({"measure_covariates": False}),
    "short_trial_4wk": make_policy({"weeks": 4}),
    "small_n_12": make_policy({"n_per_arm": 12}),
    "proteomics_only": make_policy({"clocks": list(PROTEOMIC)}),
    "epigenetics_only": make_policy({"clocks": list(EPIGENETIC)}),
    "trust_disease_clock": make_policy(analysis="trust_disease_clock"),
    "cherry_pick_best_clock": make_policy(analysis="cherry_pick"),
    "average_all_clocks": make_policy(analysis="pooled_mean"),
    "null": null_policy,
    "always_yes": always_yes_policy,
}
TRAPS = {
    "null": "smallest trial, ignore the data, always answer: no effect",
    "always_yes": "smallest trial, ignore the data, always answer: 1.2 years younger",
    "no_placebo": "pre/post change in the treated arm only, minus calendar time",
    "batch_by_arm": "follow-up samples of each arm run in their own batch",
    "no_covariates": "no blood cell mix or inflammation marker, so no adjustment",
    "short_trial_4wk": "stop at 4 weeks and report it as the 26-week effect",
    "small_n_12": "12 per arm",
    "proteomics_only": "one modality: the six proteomic clocks only",
    "epigenetics_only": "one modality: the two methylation clocks only",
    "trust_disease_clock": "headline the clock trained in the disease being treated",
    "cherry_pick_best_clock": "report whichever clock shows the biggest reversal",
    "average_all_clocks": "average every clock instead of checking that modalities agree",
}


def run_episode(env, policy) -> tuple[float, dict]:
    spec = env.reset()
    obs, _, _, _ = env.step(policy(spec))
    _, reward, done, info = env.step(policy(spec, obs))
    assert done
    return reward, info
