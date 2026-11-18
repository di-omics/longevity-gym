"""Shortcut check: can a policy that memorises, instead of estimating, beat the reference?

Two learned policies, trained only on what an agent legitimately gets: the task text, the rows
of its own trials, and the truth that the env reveals after each finished episode.
  memoriser         recognises the hidden archetype from the clock fingerprint and answers with
                    the median true effect it has seen for that archetype, dose and cohort
  classify_regress  recognises the archetype the same way, then predicts the effect with a
                    linear model fitted inside that archetype
Both are trained on seeds 20000 to 22399 and scored on other seeds. The point is not that
learning is cheating (learning which clocks to believe is the goal), but to check two things:
that the hidden potency stops pure memorising from winning, and that the design lessons on the
QC card still hold for a learner.
"""
from __future__ import annotations

import re

import numpy as np

from .clocks import CLOCK_NAMES
from .env import make
from .interventions import GEROPROTECTIVE_THRESHOLD
from .policies import POLICIES, REFERENCE_DESIGN, run_episode

FEATURES = CLOCK_NAMES + ("lymphoid_z", "crp_z")
TRAIN_SEEDS = range(20000, 22400)
TEST_BLOCKS = {"seeds 0 to 399": range(0, 400), "seeds 1000 to 1399": range(1000, 1400)}
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
    """Treated-minus-placebo mean change of every clock and covariate (calendar time removed when
    there is no placebo arm)."""
    rows = obs["rows"]
    base = {r["id"]: r for r in rows if r["timepoint"] == "baseline"}
    change = {"treated": [], "placebo": []}
    for r in rows:
        if r["timepoint"] == "end":
            change[r["arm"]].append([r[f] - base[r["id"]][f] for f in FEATURES])
    treated = np.array(change["treated"]).mean(0)
    if change["placebo"]:
        return treated - np.array(change["placebo"]).mean(0)
    treated[: len(CLOCK_NAMES)] -= obs["weeks"] / 52
    return treated


def train(design, mode: str):
    """Returns a policy. mode: 'memoriser' or 'classify_regress'."""
    x, dose, cohort, archetype, truth = [], [], [], [], []
    for seed in TRAIN_SEEDS:
        env = make(seed=seed)
        spec = env.reset()
        obs, *_ = env.step(dict(design))
        *_, info = env.step({"effect_years": 0.0, "geroprotective": False})   # throwaway report
        d, c = _task_keys(spec)
        x.append(fingerprint(obs)); dose.append(d); cohort.append(c)
        archetype.append(info["intervention"]); truth.append(info["true_effect_years"])
    x, dose, cohort, archetype, truth = map(np.array, (x, dose, cohort, archetype, truth))
    cells, resid = {}, []
    for c in ("fibrosis", "healthy"):
        for d in (1, 2, 3):
            group = (cohort == c) & (dose == d)
            centres, models = [], []
            for a in sorted(set(archetype[group])):
                m = group & (archetype == a)
                centres.append(x[m].mean(0)); resid.append(x[m] - centres[-1])
                if mode == "memoriser":
                    models.append(float(np.median(truth[m])))
                else:
                    z = np.column_stack([np.ones(m.sum()), x[m]])
                    pen = np.eye(z.shape[1]); pen[0, 0] = 0.0
                    models.append(np.linalg.solve(z.T @ z + pen, z.T @ truth[m]))
            cells[(c, d)] = (np.array(centres), models)
    resid = np.vstack(resid)
    precision = np.linalg.inv(resid.T @ resid / (len(resid) - 48))

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


def shortcut_table() -> list[dict]:
    reference = {k: np.array([run_episode(make(seed=s), POLICIES["reference"])[0] for s in seeds])
                 for k, seeds in TEST_BLOCKS.items()}
    rows = [{"policy": "reference", "design": "reference design",
             **{k: {"mean": float(v.mean())} for k, v in reference.items()}}]
    for label, change in DESIGNS:
        design = {**REFERENCE_DESIGN, **change, "measure_covariates": True}
        for mode in ("memoriser", "classify_regress"):
            policy = train(design, mode)
            row = {"policy": mode, "design": label}
            for k, seeds in TEST_BLOCKS.items():
                r = np.array([run_episode(make(seed=s), policy)[0] for s in seeds])
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
           "difference to the reference on the same seeds (standard error). Positive = beats the reference.", "",
           "| policy | trial design | " + " | ".join(blocks) + " |", "|---|---|" + "---|" * len(blocks)]
    for r in rows:
        cells = []
        for k in blocks:
            c = r[k]
            cells.append(f"{c['mean']:.3f}" + (f", {c['gap']:+.3f} ({c['se']:.3f})" if "gap" in c else ""))
        out.append(f"| {r['policy']} | {r['design']} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"
