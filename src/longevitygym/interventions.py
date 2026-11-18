"""Intervention archetypes with hidden effects. Generic mechanisms, abstract dose levels 1 to 3.

These are teaching archetypes for the reward, not claims about any real drug or regimen. Each one
moves some mix of (a) true organ aging, which is what counts, and (b) things that travel with age
and leak into clocks but are not aging by this package's definition: inflammation, disease
activity, the blood cell mix, and the methylation readout itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .biology import ORGANS


@dataclass(frozen=True)
class Intervention:
    name: str
    mechanism: str
    aging: dict = field(default_factory=dict)  # organ -> years at full onset (negative = younger); "all" allowed
    aging_tau_weeks: float = 8.0
    inflam: float = 0.0          # SD units at full onset
    disease: float = 0.0         # disease activity units
    mix: float = 0.0             # blood cell mix SD units
    epi_direct: float = 0.0      # years the methylation readout is rewound without organ change
    fast_tau_weeks: float = 1.5  # onset of the non-aging effects
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

    def effects_at(self, weeks: float, dose: int, cohort: str = "fibrosis") -> dict:
        """Population-mean shifts at a time point. dose in 1..3."""
        if self.needs_disease and cohort != "fibrosis":
            return {"organ": np.zeros(len(ORGANS)), "inflam": 0.0, "disease": 0.0, "mix": 0.0, "epi_direct": 0.0}
        da, ds = self.dose_aging[dose - 1], self.dose_side[dose - 1]
        dm = (self.dose_mix or self.dose_side)[dose - 1]
        slow = 1 - np.exp(-weeks / self.aging_tau_weeks)
        fast = 1 - np.exp(-weeks / self.fast_tau_weeks)
        return {"organ": self.organ_vector() * da * slow, "inflam": self.inflam * ds * fast,
                "disease": self.disease * ds * fast, "mix": self.mix * dm * fast,
                "epi_direct": self.epi_direct * ds * slow}

    def true_effect(self, dose: int, cohort: str, weeks: float = 26.0) -> float:
        """Ground truth: change in mean organ age vs placebo, in years, at `weeks`."""
        return float(self.effects_at(weeks, dose, cohort)["organ"].mean())


INTERVENTIONS = {i.name: i for i in (
    Intervention("inert", "no biological activity"),
    Intervention("antifibrotic", "treats fibrotic lung disease; lung organ age falls with it",
                 aging={"lung": -1.0}, disease=-0.8, inflam=-0.3, needs_disease=True),
    Intervention("anti_inflammatory", "lowers systemic inflammation; organs unchanged",
                 inflam=-1.0),
    Intervention("senolytic_like", "clears senescent cells across organs",
                 aging={"all": -1.5}, aging_tau_weeks=10.0, inflam=-0.4),
    Intervention("mtor_like", "slows growth signalling; top dose suppresses lymphocytes",
                 aging={"all": -1.2}, dose_aging=(0.6, 1.0, 0.6), mix=-1.5, dose_mix=(0.0, 0.3, 1.2)),
    Intervention("reprogramming_like", "partial epigenetic reset; methylation moves far more than organs",
                 aging={"all": -0.8}, aging_tau_weeks=6.0, epi_direct=-6.0),
    Intervention("immune_mobilizer", "shifts the blood cell mix toward lymphocytes; organs unchanged",
                 mix=2.0),
    Intervention("restriction_like", "dietary restriction mimetic; slow, broad effect",
                 aging={"all": -1.8}, aging_tau_weeks=12.0, inflam=-0.3),
)}

GEROPROTECTIVE_THRESHOLD = -0.5  # years at 26 weeks
