"""clock_trial: design a small trial of an unknown intervention, read the clocks, and say what it did.

Episode = two steps.
  reset() -> task: a coded compound, its assigned dose level, the cohort, the menu of clocks.
  step(design) -> per-sample clock readings (and covariates, if you paid for them).
  step(report) -> reward. Truth is revealed only in the final info.

The question is always the same: by how many years does this compound change biological age
(mean organ age, by definition) at 26 weeks, relative to placebo, and is that change at least
half a year younger (geroprotective)? A clock moving is evidence, not the answer.
"""
from __future__ import annotations

import numpy as np

from .biology import N_CPG, N_PROT, ORGANS, PANEL, methylome, proteome, sample_cohort
from .clocks import CLOCK_NAMES, clocks, read_clocks
from .interventions import GEROPROTECTIVE_THRESHOLD, INTERVENTIONS

WEEK_OPTIONS = (4, 12, 26)
HORIZON_WEEKS = 26
COST_PER_PARTICIPANT = 0.05 / 120


class ClockTrialEnv:
    name = "clock_trial"

    def __init__(self, seed: int = 0, intervention: str | None = None, cohort: str | None = None,
                 dose: int | None = None):
        self.seed = seed
        rng = np.random.default_rng([seed, 1])
        names = sorted(INTERVENTIONS)
        self.intervention = INTERVENTIONS[intervention or names[int(rng.integers(len(names)))]]
        self.cohort = cohort or ("fibrosis" if rng.random() < 0.5 else "healthy")
        self.dose = int(dose or rng.integers(1, 4))
        self.code = f"LG-{int(rng.integers(100, 1000))}"
        self._stage = "design"
        self._design = None

    # ------------------------------------------------------------------ spec
    def spec(self) -> dict:
        return {
            "env": self.name,
            "question": ("Estimate the change in biological age (years, treated minus placebo) caused by "
                         f"compound {self.code} at dose level {self.dose} after {HORIZON_WEEKS} weeks, and call it "
                         f"geroprotective if the change is {GEROPROTECTIVE_THRESHOLD} years or more negative."),
            "cohort": {"fibrosis": "adults 45 to 80 with fibrotic lung disease",
                       "healthy": "healthy adults 45 to 80"}[self.cohort],
            "clocks": {n: {"family": c.family, "target": c.target, "trained_on": c.trained_on,
                           "analog_of": c.analog_of} for n, c in clocks().items()},
            "design_schema": {"n_per_arm": "int 8..150", "placebo": "bool", "weeks": list(WEEK_OPTIONS),
                              "batch_layout": ["randomized", "by_arm"],
                              "measure_covariates": "bool (blood cell mix + CRP-like inflammation marker)",
                              "clocks": "list of clock names"},
            "report_schema": {"effect_years": "float", "geroprotective": "bool"},
            "cost": f"{COST_PER_PARTICIPANT:.6f} reward per enrolled participant",
        }

    def reset(self) -> dict:
        self._stage, self._design = "design", None
        return {"stage": "design", **self.spec()}

    # ------------------------------------------------------------------ step
    def step(self, action: dict):
        if self._stage == "design":
            return self._run_trial(action)
        if self._stage == "report":
            return self._score(action)
        raise RuntimeError("episode is over; call reset()")

    def _validate(self, a: dict) -> dict:
        d = {"n_per_arm": int(a.get("n_per_arm", 40)), "placebo": bool(a.get("placebo", True)),
             "weeks": int(a.get("weeks", 26)), "batch_layout": a.get("batch_layout", "randomized"),
             "measure_covariates": bool(a.get("measure_covariates", False)),
             "clocks": list(a.get("clocks", CLOCK_NAMES))}
        if not 8 <= d["n_per_arm"] <= 150:
            raise ValueError("n_per_arm must be 8..150")
        if d["weeks"] not in WEEK_OPTIONS:
            raise ValueError(f"weeks must be one of {WEEK_OPTIONS}")
        if d["batch_layout"] not in ("randomized", "by_arm"):
            raise ValueError("batch_layout must be randomized or by_arm")
        bad = [c for c in d["clocks"] if c not in CLOCK_NAMES]
        if bad or not d["clocks"]:
            raise ValueError(f"unknown or empty clocks: {bad}")
        return d

    def _run_trial(self, action: dict):
        d = self._design = self._validate(action)
        rng = np.random.default_rng([self.seed, 2])
        # plate effects: random per feature, plus a systematic part that lands on the aging axis
        # (signal compression or drift between runs). Assumed ~1 to 2 clock-years SD per batch.
        prot_batch = rng.normal(0, 0.25, (3, N_PROT)) + np.outer(rng.normal(0, 0.15, 3), PANEL.prot_age_w)
        cpg_batch = rng.normal(0, 0.12, (3, N_CPG)) + np.outer(rng.normal(0, 0.12, 3), PANEL.cpg_age_w)
        arms = (["treated", "placebo"] if d["placebo"] else ["treated"])
        rows = []
        for k, arm in enumerate(arms):
            # the same people for any n (first n of 150), so policies are compared on paired cohorts
            prng = np.random.default_rng([self.seed, 3, k])
            full = sample_cohort(prng, 150, disease="fibrosis" if self.cohort == "fibrosis" else "none")
            c = _subset(full, d["n_per_arm"])
            rng = np.random.default_rng([self.seed, 4, k])
            n, w = c.n, d["weeks"]
            base_b = np.zeros(n, int)
            xp0, xm0 = proteome(c, rng, prot_batch[base_b]), methylome(c, rng, cpg_batch[base_b])
            cov0 = self._covariates(c, rng)
            # advance time
            resp = np.clip(rng.normal(1.0, 0.3, n), 0, None)
            eff = (self.intervention.effects_at(w, self.dose, self.cohort) if arm == "treated"
                   else {"organ": np.zeros(len(ORGANS)), "inflam": 0.0, "disease": 0.0, "mix": 0.0, "epi_direct": 0.0})
            c.chrono = c.chrono + w / 52
            c.organ_age = c.organ_age + w / 52 + np.outer(resp, eff["organ"]) + rng.normal(0, 0.15, c.organ_age.shape)
            c.inflam = c.inflam + rng.normal(0, 0.5, n) + resp * eff["inflam"]
            c.mix = c.mix + rng.normal(0, 0.4, n) + resp * eff["mix"]
            if self.cohort == "fibrosis":
                c.disease = np.clip(c.disease + 0.004 * w + resp * eff["disease"], 0, None)
            if d["batch_layout"] == "by_arm":
                end_b = np.full(n, 2 if arm == "treated" else 1)
            else:
                end_b = rng.integers(1, 3, n)
            xp1 = proteome(c, rng, prot_batch[end_b])
            xm1 = methylome(c, rng, cpg_batch[end_b], epi_direct=resp * eff["epi_direct"])
            cov1 = self._covariates(c, rng)
            r0, r1 = read_clocks(xp0, xm0, d["clocks"]), read_clocks(xp1, xm1, d["clocks"])
            for i in range(n):
                pid = f"{arm[0].upper()}{i:03d}"
                for tp, rr, bb, cov in (("baseline", r0, base_b, cov0), ("end", r1, end_b, cov1)):
                    row = {"id": pid, "arm": arm, "timepoint": tp, "batch": int(bb[i]),
                           **{k: round(float(v[i]), 3) for k, v in rr.items()}}
                    if d["measure_covariates"]:
                        row.update({k: round(float(v[i]), 3) for k, v in cov.items()})
                    rows.append(row)
        self._stage = "report"
        return {"stage": "report", "weeks": d["weeks"], "rows": rows,
                "note": "clock values are predicted ages in years; covariates are z-scored"}, 0.0, False, {}

    @staticmethod
    def _covariates(c, rng) -> dict:
        return {"lymphoid_z": c.mix + rng.normal(0, 0.3, c.n), "crp_z": c.inflam + rng.normal(0, 0.3, c.n)}

    def truth(self) -> dict:
        iv = self.intervention
        eff = iv.true_effect(self.dose, self.cohort, HORIZON_WEEKS)
        return {"intervention": iv.name, "mechanism": iv.mechanism, "dose": self.dose, "cohort": self.cohort,
                "true_effect_years": eff, "geroprotective": eff <= GEROPROTECTIVE_THRESHOLD}

    def _score(self, action: dict):
        est = float(action["effect_years"])
        call = bool(action["geroprotective"])
        t = self.truth()
        err = abs(est - t["true_effect_years"])
        n_total = self._design["n_per_arm"] * (2 if self._design["placebo"] else 1)
        cost = COST_PER_PARTICIPANT * n_total
        reward = 0.5 * float(np.exp(-err / 0.75)) + 0.5 * float(call == t["geroprotective"]) - cost
        self._stage = "done"
        info = {**t, "estimate": est, "call": call, "abs_error": err, "cost": cost,
                "call_correct": call == t["geroprotective"], "design": self._design}
        return {"stage": "done"}, reward, True, info


def _subset(c, n):
    from .biology import Cohort
    return Cohort(c.chrono[:n], c.organ_age[:n], c.inflam[:n], c.disease[:n], c.mix[:n],
                  c.prot_person[:n], c.cpg_person[:n])


def make(name: str = "clock_trial", seed: int = 0, **kw) -> ClockTrialEnv:
    if name != "clock_trial":
        raise KeyError(name)
    return ClockTrialEnv(seed=seed, **kw)
