"""Intervention archetypes with hidden effects. Generic mechanisms, abstract dose levels 1 to 3.

These are teaching archetypes for the reward, not models of any real drug, diet or procedure,
and which of them "work" is a coding choice. Each one moves some mix of (a) true organ aging,
which is what counts, and (b) things that leak into clocks but are not aging by this package's
definition: inflammation, fibrosis activity, the blood cell mix, and the methylation readout
itself. Every episode also draws two hidden potency multipliers (one for the aging effect, one
for everything else), so the truth is a continuous number and not one of a short list.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .biology import ORGANS

ZERO = {"organ": np.zeros(len(ORGANS)), "inflam": 0.0, "disease": 0.0, "mix": 0.0, "epi_direct": 0.0}


@dataclass(frozen=True)
class Intervention:
    name: str
    mechanism: str
    aging: dict = field(default_factory=dict)  # organ -> years at full onset (negative = younger); "all" allowed
    aging_tau_weeks: float = 8.0
    inflam: float = 0.0          # SD units at full onset
    disease: float = 0.0         # fibrosis activity units
    mix: float = 0.0             # blood cell mix SD units
    epi_direct: float = 0.0      # years the methylation readout is rewound without organ change
    fast_tau_weeks: float = 1.5  # onset of inflammation, fibrosis and cell-mix effects
    dose_aging: tuple = (0.5, 1.0, 1.3)
    dose_side: tuple = (0.5, 1.0, 1.3)
    dose_mix: tuple | None = None  # optional separate dose curve for the cell-mix shift
    needs_disease: bool = False    # acts only where there is disease to treat

    def organ_vector(self) -> np.ndarray:
        v = np.full(len(ORGANS), float(self.aging.get("all", 0.0)))
        for k, val in self.aging.items():
            if k != "all":
                v[ORGANS.index(k)] += val
        return v

    def effects_at(self, weeks: float, dose: int, cohort: str, potency=(1.0, 1.0)) -> dict:
        """Population-mean shifts at a time point. dose in 1..3; potency = (aging, everything else)."""
        if self.needs_disease and cohort != "fibrosis":
            return dict(ZERO)
        pa, ps = potency
        da, ds = self.dose_aging[dose - 1], self.dose_side[dose - 1]
        dm = (self.dose_mix or self.dose_side)[dose - 1]
        slow = 1 - np.exp(-weeks / self.aging_tau_weeks)
        fast = 1 - np.exp(-weeks / self.fast_tau_weeks)
        return {"organ": self.organ_vector() * da * pa * slow, "inflam": self.inflam * ds * ps * fast,
                "disease": self.disease * ds * ps * fast, "mix": self.mix * dm * ps * fast,
                "epi_direct": self.epi_direct * ds * ps * slow}

    def true_effect(self, dose: int, cohort: str, weeks: float = 26.0, potency=(1.0, 1.0)) -> float:
        """Ground truth: change in mean organ age vs placebo, in years, at `weeks`."""
        return float(self.effects_at(weeks, dose, cohort, potency)["organ"].mean())


INTERVENTIONS = {i.name: i for i in (
    Intervention("inert", "no biological activity"),
    Intervention("antifibrotic", "lowers fibrosis activity; only the lung gets slightly younger",
                 aging={"lung": -1.0}, disease=-0.8, inflam=-0.3, needs_disease=True),
    Intervention("anti_inflammatory", "lowers systemic inflammation; organs unchanged",
                 inflam=-1.0),
    Intervention("senolytic_like", "coded to make every organ younger; also lowers inflammation",
                 aging={"all": -1.5}, aging_tau_weeks=10.0, inflam=-0.4),
    Intervention("mtor_like", "coded to make every organ younger; the top dose suppresses lymphocytes",
                 aging={"all": -1.2}, dose_aging=(0.6, 1.0, 0.6), mix=-1.5, dose_mix=(0.0, 0.3, 1.2)),
    Intervention("reprogramming_like", "rewinds the methylation readout far more than the organs",
                 aging={"all": -0.8}, aging_tau_weeks=6.0, epi_direct=-6.0),
    Intervention("immune_mobilizer", "shifts the blood cell mix toward lymphocytes; organs unchanged",
                 mix=2.0),
    Intervention("restriction_like", "coded to make every organ younger, slowly; lowers inflammation a little",
                 aging={"all": -1.8}, aging_tau_weeks=12.0, inflam=-0.3),
)}

GEROPROTECTIVE_THRESHOLD = -0.5  # years at 26 weeks
POTENCY_RANGE = (0.25, 1.75)
