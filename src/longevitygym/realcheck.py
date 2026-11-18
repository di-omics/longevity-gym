"""How the simulator's clock noise compares with real clock readouts, and a calibrated noise profile.

The only real numbers in this repo are the aggregates below. They were computed from the public
supplementary tables of reference [1] in the README (Zhavoronkov et al., Nature Biotechnology
2026, an open access article under CC BY 4.0) by tools/real_targets.py. No participant-level data is stored here, and the
168 unlabeled samples of the paper's prediction table were not linked back to participants.

What the aggregates are:
  change_sd   the SD of one person's change in a clock reading between two visits 2 to 12 weeks
              apart, estimated from the paper's published Mann-Whitney statistics under a normal
              model (estimate, and the 5th and 95th percentile of a parametric bootstrap)
  sample_sd   the SD of a clock's readings over the 168 samples
  corr        the correlation between clocks over the 168 samples

What they are used for: (1) a report of how far the simulator's default noise is from these
numbers, and (2) an optional noise profile, make(..., noise="calibrated"), that adds reading
noise to every clock until its change-score SD equals the real estimate for the clock whose
recipe it imitates. Two things in that profile are assumptions and not measurements: half of
the added variance is shared by the clocks of one modality in a sample, and the two methylation
clocks (for which [1] has no data) get the mean target of the four chronological proteomic ones.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .clocks import CLOCK_NAMES, PROTEOMIC

REAL = {
    "n_samples": 168,
    "change_sd": {
        "ProtAge": {"estimate": 2.03, "boot_p05": 1.65, "boot_p95": 2.25},
        "OrganAge_chrono": {"estimate": 2.61, "boot_p05": 2.09, "boot_p95": 2.99},
        "ipfP3GPT": {"estimate": 2.82, "boot_p05": 2.24, "boot_p95": 3.24},
        "PAOPAC": {"estimate": 3.16, "boot_p05": 2.54, "boot_p95": 3.53},
        "OrganAge_mortality": {"estimate": 3.70, "boot_p05": 3.01, "boot_p95": 4.12},
        "PAC": {"estimate": 4.31, "boot_p05": 3.48, "boot_p95": 4.91},
    },
    "sample_sd": {"ProtAge": 5.05, "OrganAge_chrono": 5.07, "ipfP3GPT": 5.12, "PAOPAC": 5.74,
                  "OrganAge_mortality": 12.50, "PAC": 13.64},
    "corr": {
        "ProtAge": {"ProtAge": 1.00, "OrganAge_chrono": 0.87, "ipfP3GPT": 0.82, "PAOPAC": 0.90, "OrganAge_mortality": 0.51, "PAC": 0.48},
        "OrganAge_chrono": {"ProtAge": 0.87, "OrganAge_chrono": 1.00, "ipfP3GPT": 0.89, "PAOPAC": 0.79, "OrganAge_mortality": 0.27, "PAC": 0.27},
        "ipfP3GPT": {"ProtAge": 0.82, "OrganAge_chrono": 0.89, "ipfP3GPT": 1.00, "PAOPAC": 0.75, "OrganAge_mortality": 0.35, "PAC": 0.34},
        "PAOPAC": {"ProtAge": 0.90, "OrganAge_chrono": 0.79, "ipfP3GPT": 0.75, "PAOPAC": 1.00, "OrganAge_mortality": 0.55, "PAC": 0.56},
        "OrganAge_mortality": {"ProtAge": 0.51, "OrganAge_chrono": 0.27, "ipfP3GPT": 0.35, "PAOPAC": 0.55, "OrganAge_mortality": 1.00, "PAC": 0.94},
        "PAC": {"ProtAge": 0.48, "OrganAge_chrono": 0.27, "ipfP3GPT": 0.34, "PAOPAC": 0.56, "OrganAge_mortality": 0.94, "PAC": 1.00},
    },
}
# simulated clock -> the real clock whose recipe it imitates
ANALOG = {"prot_sparse_chrono": "ProtAge", "prot_dense_chrono": "OrganAge_chrono", "prot_dense_chrono_b": "ipfP3GPT",
          "prot_organ_chrono": "PAOPAC", "prot_sparse_mortality": "OrganAge_mortality", "prot_age_mortality": "PAC"}
CHRONO_REAL = ("ProtAge", "OrganAge_chrono", "ipfP3GPT", "PAOPAC")
SHARED_FRACTION = 0.5      # assumed share of the added noise variance common to one modality in a sample
AGE_WINDOW = (55.5, 78.5)  # simulated ages kept for the cross-sample comparison (SD 6.6 years, as in [1])


def target_change_sd() -> dict:
    """The change-score SD each simulated clock is calibrated to, in years."""
    out = {name: REAL["change_sd"][real]["estimate"] for name, real in ANALOG.items()}
    assumed = float(np.mean([REAL["change_sd"][c]["estimate"] for c in CHRONO_REAL]))
    out.update({name: round(assumed, 2) for name in CLOCK_NAMES if name not in out})
    return out


def _trial_rows(noise: str, seed: int, weeks: int = 12, layout: str = "by_arm"):
    from .env import make
    env = make(seed=seed, intervention="inert", cohort="fibrosis", noise=noise)
    obs, *_ = env.step({"n_per_arm": 150, "weeks": weeks, "plate_layout": layout})
    return obs["rows"]


def change_sd(noise: str, seeds=range(6)) -> dict:
    """SD of a placebo participant's change between two visits, per clock, within one plate."""
    sds = {name: [] for name in CLOCK_NAMES}
    for seed in seeds:
        rows = _trial_rows(noise, seed)
        base = {r["id"]: r for r in rows if r["timepoint"] == "baseline" and r["arm"] == "placebo"}
        end = [r for r in rows if r["timepoint"] == "end" and r["arm"] == "placebo"]
        for name in CLOCK_NAMES:
            sds[name].append(np.std([r[name] - base[r["id"]][name] for r in end], ddof=1))
    return {name: float(np.mean(v)) for name, v in sds.items()}


@lru_cache(maxsize=1)
def calibrated_extra_sd() -> dict:
    """Extra noise per clock reading, in years, that lifts the simulator's change-score SD to the target."""
    default, target = change_sd("default"), target_change_sd()
    return {name: float(np.sqrt(max(target[name] ** 2 - default[name] ** 2, 0.0) / 2)) for name in CLOCK_NAMES}


def cross_sample(noise: str, seeds=range(6)) -> dict:
    """SD of readings and correlations between the six proteomic clocks over simulated samples
    (both visits, both arms, ages inside AGE_WINDOW), averaged over a few simulated cohorts."""
    sds, corrs = [], []
    for seed in seeds:
        rows = [r for r in _trial_rows(noise, seed, layout="randomized") if AGE_WINDOW[0] <= r["age"] <= AGE_WINDOW[1]]
        x = np.array([[r[name] for name in PROTEOMIC] for r in rows])
        sds.append(x.std(axis=0, ddof=1)); corrs.append(np.corrcoef(x.T))
    sd, corr = np.mean(sds, axis=0), np.mean(corrs, axis=0)
    return {"sample_sd": {name: float(sd[i]) for i, name in enumerate(PROTEOMIC)},
            "corr": {a: {b: float(corr[i, j]) for j, b in enumerate(PROTEOMIC)} for i, a in enumerate(PROTEOMIC)}}


def shared_fraction_sensitivity(fractions=(0.0, 0.5, 1.0), seeds=range(600)) -> list[dict]:
    """The one free choice in the calibrated profile: how much of the added noise the clocks of a
    modality share. Reruns three policies under calibrated noise for other values of it."""
    global SHARED_FRACTION
    from .env import make
    from .policies import POLICIES, run_episode
    kept, rows = SHARED_FRACTION, []
    try:
        for fraction in fractions:
            SHARED_FRACTION = fraction
            score = {name: np.array([run_episode(make(seed=s, noise="calibrated"), POLICIES[name])[0] for s in seeds])
                     for name in ("reference", "one_clock", "proteomics_only")}
            row = {"shared_fraction": fraction, "reference": float(score["reference"].mean())}
            for name in ("one_clock", "proteomics_only"):
                d = score["reference"] - score[name]
                row[name] = {"gap": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(len(d)))}
            rows.append(row)
    finally:
        SHARED_FRACTION = kept
    return rows


def real_check() -> dict:
    out = {"real": REAL, "analog": ANALOG, "target_change_sd": target_change_sd(),
           "extra_reading_sd": calibrated_extra_sd(), "shared_fraction": SHARED_FRACTION,
           "shared_fraction_sensitivity": shared_fraction_sensitivity()}
    for noise in ("default", "calibrated"):
        out[noise] = {"change_sd": change_sd(noise), **cross_sample(noise)}
    ratios = [REAL["change_sd"][real]["estimate"] / out["default"]["change_sd"][name] for name, real in ANALOG.items()]
    out["default_too_quiet_by"] = {"min": float(min(ratios)), "max": float(max(ratios))}
    return out


def real_check_markdown(res: dict | None = None) -> str:
    res = res or real_check()
    real, d, c = res["real"], res["default"], res["calibrated"]
    out = ["# The simulator's clock noise against real clock readouts", "",
           "Real numbers: aggregates computed from the public supplementary tables of reference [1] in the README "
           "(an open access article, CC BY 4.0) by tools/real_targets.py. No participant-level data is in this repo. Simulated numbers: a "
           "fibrosis cohort given an inert compound. This compares noise only. It says nothing about any drug.", "",
           "## Noise of a change score (years): SD of one person's change between two visits", "",
           "| simulated clock | real clock it imitates | real estimate (5th to 95th percentile) | simulator, default "
           "| real / default | simulator, calibrated |", "|---|---|---|---|---|---|"]
    for name, real_name in res["analog"].items():
        t = real["change_sd"][real_name]
        out.append(f"| {name} | {real_name} | {t['estimate']:.2f} ({t['boot_p05']:.2f} to {t['boot_p95']:.2f}) | "
                   f"{d['change_sd'][name]:.2f} | {t['estimate'] / d['change_sd'][name]:.1f} | {c['change_sd'][name]:.2f} |")
    for name in CLOCK_NAMES:
        if name not in res["analog"]:
            out.append(f"| {name} | none in [1] | assumed {res['target_change_sd'][name]:.2f} | {d['change_sd'][name]:.2f} | "
                       f"| {c['change_sd'][name]:.2f} |")
    out += ["", "The real estimate is indirect: it is backed out of published Mann-Whitney statistics under a normal "
            "model with one SD per clock, and visits there are 2 to 12 weeks apart. The calibrated column matches "
            "the real estimate by construction.", "",
            "## Not used for calibration: SD of readings over samples (years)", "",
            "| simulated clock | real clock | real, 168 samples | simulator, default | simulator, calibrated |",
            "|---|---|---|---|---|"]
    for name, real_name in res["analog"].items():
        out.append(f"| {name} | {real_name} | {real['sample_sd'][real_name]:.1f} | {d['sample_sd'][name]:.1f} | "
                   f"{c['sample_sd'][name]:.1f} |")
    out += ["", "## Not used for calibration: correlation between clocks over samples", "",
            "Each cell: real / simulator default / simulator calibrated.", "",
            "| | " + " | ".join(res["analog"][n] for n in PROTEOMIC) + " |", "|---|" + "---|" * len(PROTEOMIC)]
    for a in PROTEOMIC:
        cells = []
        for b in PROTEOMIC:
            ra, rb = res["analog"][a], res["analog"][b]
            cells.append("1" if a == b else f"{real['corr'][ra][rb]:.2f} / {d['corr'][a][b]:.2f} / {c['corr'][a][b]:.2f}")
        out.append(f"| {res['analog'][a]} | " + " | ".join(cells) + " |")
    out += ["", f"Simulated samples are restricted to ages {AGE_WINDOW[0]} to {AGE_WINDOW[1]} so that the age spread is "
            "close to the real cohort's (SD 6.65 years).", "",
            "## The one free choice: how much of the added noise the clocks share", "",
            f"The calibrated profile assumes {res['shared_fraction']:.1f}. The open data cannot say. Reference reward "
            "and the gap to two shortcuts under calibrated noise, 600 seeds, for three values:", "",
            "| share of added noise common to one modality | reference reward | one clock alone: gap (SE) "
            "| six proteomic clocks only: gap (SE) |", "|---|---|---|---|"]
    for r in res["shared_fraction_sensitivity"]:
        out.append(f"| {r['shared_fraction']:.1f} | {r['reference']:.3f} | {r['one_clock']['gap']:+.3f} "
                   f"({r['one_clock']['se']:.3f}) | {r['proteomics_only']['gap']:+.3f} ({r['proteomics_only']['se']:.3f}) |")
    out.append("")
    return "\n".join(out)
