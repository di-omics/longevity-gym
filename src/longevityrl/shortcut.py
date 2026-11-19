"""Shortcut check: can a policy that memorises, instead of estimating, beat the reference?

Two learned policies, trained only on what an agent legitimately gets: the task text, the rows
of its own trials, and the truth that the env reveals after each finished episode.
  memoriser         recognises the hidden archetype from the clock fingerprint and answers with
                    the median true effect it has seen for that archetype, dose and cohort
  classify_regress  recognises the archetype the same way, then predicts the effect with a
                    linear model fitted inside that archetype
Both are refitted on every run from seeds 20000 to 22399 and scored on other seeds. A third
block scores them with the aging potency forced to 2.5, outside the range they were trained
on: a policy that reads the clocks should not care, a policy that has learned this simulator's
task mix should.
"""
from __future__ import annotations

import re

import numpy as np

from .clocks import CLOCK_NAMES
from .env import make
from .interventions import GEROPROTECTIVE_THRESHOLD
from .policies import COVARIATES, POLICIES, REFERENCE_DESIGN, clock_effect, covariate_shift, run_episode

TRAIN_SEEDS = range(20000, 22400)
OFF_RANGE_POTENCY = (2.5, 1.0)
TEST_BLOCKS = {
    "seeds 0 to 399": (range(0, 400), None),
    "seeds 1000 to 1399": (range(1000, 1400), None),
    "seeds 1000 to 1399, aging potency 2.5": (range(1000, 1400), OFF_RANGE_POTENCY),
}
DESIGNS = (
    ("same design as the reference", {}),
    ("12 per arm", {"n_per_arm": 12}),
    ("no placebo arm", {"placebo": False}),
    ("stop at 4 weeks", {"weeks": 4}),
    ("plates by arm", {"plate_layout": "by_arm"}),
)


def _task_keys(spec):
    dose = int(re.search(r"dose level (\d)", spec["question"]).group(1))
    return dose, ("fibrosis" if "fibrotic" in spec["cohort"] else "healthy")


def fingerprint(obs) -> np.ndarray:
    """Plate-adjusted treated-minus-placebo change of every clock, and the shift of both covariates."""
    rows, weeks = obs["rows"], obs["weeks"]
    return np.array([clock_effect(rows, c, weeks) for c in CLOCK_NAMES] + [covariate_shift(rows, c) for c in COVARIATES])


def collect(design) -> dict:
    """One throwaway episode per training seed: fingerprint, task keys and the truth revealed at the end."""
    x, dose, cohort, archetype, truth = [], [], [], [], []
    for seed in TRAIN_SEEDS:
        env = make(seed=seed)
        spec = env.reset()
        obs, *_ = env.step(dict(design))
        *_, info = env.step({"effect_years": 0.0, "geroprotective": False})
        d, c = _task_keys(spec)
        x.append(fingerprint(obs)); dose.append(d); cohort.append(c)
        archetype.append(info["intervention"]); truth.append(info["true_effect_years"])
    return {"x": np.array(x), "dose": np.array(dose), "cohort": np.array(cohort),
            "archetype": np.array(archetype), "truth": np.array(truth)}


def fit(data: dict, design, mode: str):
    """Returns a policy. mode: 'memoriser' or 'classify_regress'."""
    x, truth = data["x"], data["truth"]
    cells, resid, n_cells = {}, [], 0
    for c in ("fibrosis", "healthy"):
        for d in (1, 2, 3):
            group = (data["cohort"] == c) & (data["dose"] == d)
            centres, models = [], []
            for a in sorted(set(data["archetype"][group])):
                m = group & (data["archetype"] == a)
                centres.append(x[m].mean(0)); resid.append(x[m] - centres[-1]); n_cells += 1
                if mode == "memoriser":
                    models.append(float(np.median(truth[m])))
                else:
                    z = np.column_stack([np.ones(m.sum()), x[m]])
                    pen = np.eye(z.shape[1]); pen[0, 0] = 0.0
                    models.append(np.linalg.solve(z.T @ z + pen, z.T @ truth[m]))
            cells[(c, d)] = (np.array(centres), models)
    resid = np.vstack(resid)
    precision = np.linalg.inv(resid.T @ resid / (len(resid) - n_cells))

    def policy(spec, obs=None):
        if obs is None:
            return dict(design)
        d, c = _task_keys(spec)
        centres, models = cells[(c, d)]
        f = fingerprint(obs)
        diff = centres - f
        k = int(np.argmin(np.einsum("ij,jk,ik->i", diff, precision, diff)))
        est = models[k] if mode == "memoriser" else float(models[k][0] + f @ models[k][1:])
        est = round(float(est), 3)
        return {"effect_years": est, "geroprotective": bool(est <= GEROPROTECTIVE_THRESHOLD)}
    return policy


def _score(policy, seeds, potency) -> np.ndarray:
    kw = {} if potency is None else {"potency": potency}
    return np.array([run_episode(make(seed=s, **kw), policy)[0] for s in seeds])


def shortcut_table() -> list[dict]:
    reference = {k: _score(POLICIES["reference"], seeds, potency) for k, (seeds, potency) in TEST_BLOCKS.items()}
    rows = [{"policy": "reference", "design": "reference design",
             **{k: {"mean": float(v.mean())} for k, v in reference.items()}}]
    for label, change in DESIGNS:
        design = {**REFERENCE_DESIGN, **change}
        data = collect(design)
        for mode in ("memoriser", "classify_regress"):
            policy = fit(data, design, mode)
            row = {"policy": mode, "design": label}
            for k, (seeds, potency) in TEST_BLOCKS.items():
                r = _score(policy, seeds, potency)
                d = r - reference[k]
                row[k] = {"mean": float(r.mean()), "gap": float(d.mean()),
                          "se": float(d.std(ddof=1) / np.sqrt(len(d)))}
            rows.append(row)
    return rows


def shortcut_markdown(rows=None) -> str:
    rows = rows or shortcut_table()
    blocks = list(TEST_BLOCKS)
    out = ["# Shortcut check: learned policies against the reference", "",
           f"Trained on seeds {TRAIN_SEEDS.start} to {TRAIN_SEEDS.stop - 1}. Each cell: mean reward, then the paired "
           "difference to the reference on the same seeds (standard error). Positive = beats the reference. In the "
           "last column the hidden aging potency is forced to 2.5, outside the range of 0.25 to 1.75 that the "
           "policies were trained on.", "",
           "| policy | trial design | " + " | ".join(blocks) + " |", "|---|---|" + "---|" * len(blocks)]
    for r in rows:
        cells = []
        for k in blocks:
            c = r[k]
            cells.append(f"{c['mean']:.3f}" + (f", {c['gap']:+.3f} ({c['se']:.3f})" if "gap" in c else ""))
        out.append(f"| {r['policy']} | {r['design']} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"
