"""clock_trial: design a small simulated trial of an unknown intervention, read the clocks, say what it did.

One env object is one episode, in two steps.
  reset() -> task: a coded simulated compound, its dose level, the cohort, the menu of clocks.
  step(design) -> per-sample clock readings (and two covariates, if you asked for them).
  step(report) -> reward. Truth is revealed only in the final info.

The question is always the same: by how many years does this compound change biological age
(mean organ age, by this simulator's definition) at 26 weeks, relative to placebo, and is that
change at least half a year younger (geroprotective)? A clock moving is evidence, not the answer.
"""
from __future__ import annotations

import math

import numpy as np

from .biology import Cohort, N_CPG, N_PROT, ORGANS, PANEL, methylome, proteome, sample_cohort
from .clocks import CLOCK_NAMES, clock_cards, clocks, read_clocks
from .interventions import GEROPROTECTIVE_THRESHOLD, INTERVENTIONS, POTENCY_RANGE, ZERO

WEEK_OPTIONS = (4, 12, 26)
HORIZON_WEEKS = 26
MAX_PER_ARM = 150
COST_PER_PARTICIPANT = 0.05 / 120
COHORTS = {"fibrosis": "adults 45 to 80 with fibrotic lung disease", "healthy": "healthy adults 45 to 80"}
DESIGN_DEFAULTS = {"n_per_arm": 40, "placebo": True, "weeks": 26, "plate_layout": "randomized",
                   "measure_covariates": False, "clocks": list(CLOCK_NAMES)}
REPORT_KEYS = ("effect_years", "geroprotective")
NOISE_PROFILES = ("default", "calibrated")


def _is_int(v) -> bool:
    return isinstance(v, (int, np.integer)) and not isinstance(v, bool)


class ClockTrialEnv:
    name = "clock_trial"

    def __init__(self, seed: int = 0, intervention: str | None = None, cohort: str | None = None,
                 dose: int | None = None, potency: tuple | None = None, noise: str = "default"):
        """noise: "default" (the simulator's own assumed noise) or "calibrated" (extra reading noise
        on every clock, sized from real clock readouts; see realcheck.py)."""
        if noise not in NOISE_PROFILES:
            raise ValueError(f"noise must be one of {NOISE_PROFILES}")
        self.noise = noise
        if not (_is_int(seed) and seed >= 0):
            raise ValueError("seed must be a non-negative int")
        self.seed = int(seed)
        rng = np.random.default_rng([self.seed, 1])
        names = sorted(INTERVENTIONS)
        # every draw is always consumed, so a forced argument never shifts the others
        drawn_iv = names[int(rng.integers(len(names)))]
        drawn_cohort = "fibrosis" if rng.random() < 0.5 else "healthy"
        drawn_dose = int(rng.integers(1, 4))
        self.code = f"TOY-{int(rng.integers(100, 1000))}"
        drawn_potency = (float(rng.uniform(*POTENCY_RANGE)), float(rng.uniform(*POTENCY_RANGE)))
        if intervention is not None and intervention not in INTERVENTIONS:
            raise ValueError(f"unknown intervention {intervention!r}")
        if cohort is not None and cohort not in COHORTS:
            raise ValueError(f"cohort must be one of {sorted(COHORTS)}")
        if dose is not None and not (_is_int(dose) and 1 <= dose <= 3):
            raise ValueError("dose must be 1, 2 or 3")
        if potency is not None:
            ok = isinstance(potency, (tuple, list)) and len(potency) == 2 and all(
                isinstance(q, (int, float)) and not isinstance(q, bool) and math.isfinite(q) and q > 0 for q in potency)
            if not ok:
                raise ValueError("potency must be two finite positive numbers (aging, everything else)")
        self.intervention = INTERVENTIONS[intervention if intervention is not None else drawn_iv]
        self.cohort = cohort if cohort is not None else drawn_cohort
        self.dose = int(dose) if dose is not None else drawn_dose
        self.potency = tuple(float(p) for p in potency) if potency is not None else drawn_potency
        self._stage = "design"
        self._design = None
        self._enrolled = 0

    # ------------------------------------------------------------------ spec
    def spec(self) -> dict:
        return {
            "env": self.name,
            "question": ("Estimate the change in biological age (years, treated minus placebo) caused by "
                         f"simulated compound {self.code} at dose level {self.dose} after {HORIZON_WEEKS} weeks, "
                         f"and call it geroprotective if the change is {GEROPROTECTIVE_THRESHOLD} years or lower."),
            "cohort": COHORTS[self.cohort],
            "clocks": {n: {"family": c.family, "target": c.target, "inputs": c.inputs,
                           "calibration": dict(clock_cards()[n])} for n, c in clocks().items()},
            "calibration_note": ("measured in simulated healthy people: years the clock's reading moves per year "
                                 "of true organ aging, per SD of the blood cell mix covariate and per SD of the "
                                 "inflammation covariate; how a clock reads disease activity is not known"),
            "design_schema": {"n_per_arm": f"int 8..{MAX_PER_ARM}", "placebo": "bool", "weeks": list(WEEK_OPTIONS),
                              "plate_layout": ["randomized", "by_arm"],
                              "measure_covariates": "bool (blood cell mix and an inflammation marker)",
                              "clocks": "list of clock names"},
            "design_defaults": {**DESIGN_DEFAULTS, "clocks": list(CLOCK_NAMES)},
            "report_schema": {"effect_years": "finite number",
                              "geroprotective": f"bool, must equal effect_years <= {GEROPROTECTIVE_THRESHOLD}"},
            "cost": f"{COST_PER_PARTICIPANT:.6f} reward per enrolled participant",
        }

    def reset(self) -> dict:
        if self._stage != "design":
            raise RuntimeError("one env object is one episode: make a new env (new seed) for a new task")
        return {"stage": "design", **self.spec()}

    # ------------------------------------------------------------------ step
    def step(self, action: dict):
        if self._stage == "design":
            return self._run_trial(action)
        if self._stage == "report":
            return self._score(action)
        raise RuntimeError("episode is over: make a new env (new seed) for a new task")

    def _validate_design(self, a) -> dict:
        if not isinstance(a, dict):
            raise ValueError("a design must be a dict")
        if not all(isinstance(k, str) for k in a):
            raise ValueError("design keys must be strings")
        unknown = sorted(set(a) - set(DESIGN_DEFAULTS))
        if unknown:
            hint = " (this env is waiting for a design, not a report)" if set(unknown) & set(REPORT_KEYS) else ""
            raise ValueError(f"unknown design keys {unknown}{hint}")
        d = {**DESIGN_DEFAULTS, "clocks": list(CLOCK_NAMES), **a}
        if not (_is_int(d["n_per_arm"]) and 8 <= d["n_per_arm"] <= MAX_PER_ARM):
            raise ValueError(f"n_per_arm must be an int in 8..{MAX_PER_ARM}")
        if not (_is_int(d["weeks"]) and d["weeks"] in WEEK_OPTIONS):
            raise ValueError(f"weeks must be one of {WEEK_OPTIONS}")
        for key in ("placebo", "measure_covariates"):
            if not isinstance(d[key], bool):
                raise ValueError(f"{key} must be true or false (a bool, not a string or number)")
        if not isinstance(d["plate_layout"], str) or d["plate_layout"] not in ("randomized", "by_arm"):
            raise ValueError("plate_layout must be 'randomized' or 'by_arm'")
        cl = d["clocks"]
        if (not isinstance(cl, (list, tuple)) or not cl or not all(isinstance(c, str) for c in cl)
                or len(set(cl)) != len(cl) or any(c not in CLOCK_NAMES for c in cl)):
            raise ValueError(f"clocks must be a non-empty list of distinct names from {list(CLOCK_NAMES)}")
        d["n_per_arm"], d["weeks"], d["clocks"] = int(d["n_per_arm"]), int(d["weeks"]), list(cl)
        return d

    def _run_trial(self, action):
        d = self._validate_design(action)
        self._design = d
        n, w = d["n_per_arm"], d["weeks"]
        arms = ["treated", "placebo"] if d["placebo"] else ["treated"]
        self._enrolled += n * len(arms)
        # plate effects: random per feature, plus a systematic part along the aging axis
        prng = np.random.default_rng([self.seed, 2])
        prot_plate = prng.normal(0, 0.25, (3, N_PROT)) + np.outer(prng.normal(0, 0.15, 3), PANEL.prot_age_w)
        cpg_plate = prng.normal(0, 0.12, (3, N_CPG)) + np.outer(prng.normal(0, 0.12, 3), PANEL.cpg_age_w)
        rows = []
        for k, arm in enumerate(("treated", "placebo")):
            if arm not in arms:
                continue
            # Everything random is drawn for MAX_PER_ARM people in a fixed order and then cut to n, so
            # designs that differ in size, layout or duration are compared on the same people and noise.
            rng = np.random.default_rng([self.seed, 3, k])
            c0 = sample_cohort(rng, MAX_PER_ARM, disease="fibrosis" if self.cohort == "fibrosis" else "none")
            m = c0.n
            resp = np.clip(rng.normal(1.0, 0.3, m), 0, None)
            organ_drift, inflam_drift, mix_drift = rng.normal(0, 0.15, c0.organ_age.shape), rng.normal(0, 0.5, m), rng.normal(0, 0.4, m)
            random_plate = rng.integers(1, 3, m)
            cov_noise = rng.normal(0, 0.3, (4, m))
            xp0, xm0 = proteome(c0, rng, prot_plate[0]), methylome(c0, rng, cpg_plate[0])
            eff = self.intervention.effects_at(w, self.dose, self.cohort, self.potency) if arm == "treated" else ZERO
            disease1 = c0.disease
            if self.cohort == "fibrosis":
                disease1 = np.clip(c0.disease + 0.004 * w + resp * eff["disease"], 0, None)
            c1 = Cohort(c0.chrono + w / 52,
                        c0.organ_age + w / 52 + np.outer(resp, eff["organ"]) + organ_drift,
                        c0.inflam + inflam_drift + resp * eff["inflam"], disease1,
                        c0.mix + mix_drift + resp * eff["mix"], c0.prot_person, c0.cpg_person)
            plate1 = np.full(m, 2 if arm == "treated" else 1) if d["plate_layout"] == "by_arm" else random_plate
            xp1 = proteome(c1, rng, prot_plate[plate1])
            xm1 = methylome(c1, rng, cpg_plate[plate1], epi_direct=resp * eff["epi_direct"])
            r0 = read_clocks(xp0, xm0, c0.chrono, d["clocks"])
            r1 = read_clocks(xp1, xm1, c1.chrono, d["clocks"])
            if self.noise == "calibrated":
                self._add_reading_noise((r0, r1), k, m)
            cov0 = {"lymphoid_z": c0.mix + cov_noise[0], "crp_z": c0.inflam + cov_noise[1]}
            cov1 = {"lymphoid_z": c1.mix + cov_noise[2], "crp_z": c1.inflam + cov_noise[3]}
            for i in range(n):
                pid = f"{arm[0].upper()}{i:03d}"
                for tp, cc, rr, plate, cov in (("baseline", c0, r0, 0, cov0), ("end", c1, r1, int(plate1[i]), cov1)):
                    row = {"id": pid, "arm": arm, "timepoint": tp, "plate": plate, "age": round(float(cc.chrono[i]), 2),
                           **{name: round(float(v[i]), 3) for name, v in rr.items()}}
                    if d["measure_covariates"]:
                        row.update({name: round(float(v[i]), 3) for name, v in cov.items()})
                    rows.append(row)
        self._stage = "report"
        return {"stage": "report", "weeks": w, "rows": rows,
                "note": "clock values are predicted ages in years; covariates are in reference SD units"}, 0.0, False, {}

    def _add_reading_noise(self, visits, arm_index: int, m: int) -> None:
        """Calibrated profile only. A separate random stream, drawn for every clock in a fixed order,
        so the default profile is untouched and clock menus stay comparable."""
        from .realcheck import SHARED_FRACTION, calibrated_extra_sd
        extra = calibrated_extra_sd()
        rng = np.random.default_rng([self.seed, 6, arm_index])
        shared = {family: rng.normal(0, 1, (2, m)) for family in ("proteomic", "epigenetic")}
        own = {name: rng.normal(0, 1, (2, m)) for name in CLOCK_NAMES}
        for visit, readings in enumerate(visits):
            for name in readings:
                mix = SHARED_FRACTION ** 0.5 * shared[clocks()[name].family][visit] + (1 - SHARED_FRACTION) ** 0.5 * own[name][visit]
                readings[name] = readings[name] + extra[name] * mix

    def truth(self) -> dict:
        iv = self.intervention
        eff = iv.true_effect(self.dose, self.cohort, HORIZON_WEEKS, self.potency)
        return {"intervention": iv.name, "mechanism": iv.mechanism, "dose": self.dose, "cohort": self.cohort,
                "potency_aging": self.potency[0], "potency_other": self.potency[1],
                "true_effect_years": eff, "geroprotective": eff <= GEROPROTECTIVE_THRESHOLD}

    def _score(self, action):
        if not isinstance(action, dict) or set(action) != set(REPORT_KEYS):
            raise ValueError(f"a report must be a dict with exactly the keys {list(REPORT_KEYS)}")
        est, call = action["effect_years"], action["geroprotective"]
        if isinstance(est, bool) or not isinstance(est, (int, float, np.integer, np.floating)):
            raise ValueError("effect_years must be a finite number")
        try:
            finite = math.isfinite(float(est))
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("effect_years must be a finite number")
        if not isinstance(call, (bool, np.bool_)):
            raise ValueError("geroprotective must be true or false (a bool, not a string or number)")
        est, call = float(est), bool(call)
        if call != (est <= GEROPROTECTIVE_THRESHOLD):
            raise ValueError(f"geroprotective must equal effect_years <= {GEROPROTECTIVE_THRESHOLD}")
        t = self.truth()
        err = abs(est - t["true_effect_years"])
        cost = COST_PER_PARTICIPANT * self._enrolled
        reward = 0.5 * math.exp(-err / 0.75) + 0.5 * float(call == t["geroprotective"]) - cost
        self._stage = "done"
        info = {**t, "estimate": est, "call": call, "abs_error": err, "cost": cost,
                "call_correct": call == t["geroprotective"], "design": self._design}
        return {"stage": "done"}, reward, True, info


def make(name: str = "clock_trial", seed: int = 0, **kw) -> ClockTrialEnv:
    if name != "clock_trial":
        raise KeyError(name)
    return ClockTrialEnv(seed=seed, **kw)
