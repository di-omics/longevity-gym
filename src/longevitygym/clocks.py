"""Eight aging clocks, each learned from a simulated reference cohort the way real clocks are.

The six proteomic clocks are ANALOGS of the six families Insilico Medicine applied to the
rentosertib phase 2a serum proteomes (Zhavoronkov et al., Nature Biotechnology 2026): a deep
chronological clock, organ-resolved clocks trained on chronological age and on mortality, a
mortality clock, a clock trained inside a fibrosis cohort, and a sparse chronological clock.
They are not those models; they share only what was trained on what. Two things are assumptions
of this repo and not facts about the originals: that the fifth clock was trained in fibrosis
patients (read from its name), and the sparse feature set of the sixth (chosen so the six
recipes differ). Two epigenetic clocks
(chronological and mortality, in the spirit of first and second generation methylation clocks)
give an independent modality.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .biology import PANEL, ORGANS, methylome, proteome, sample_cohort


@dataclass(frozen=True)
class Clock:
    name: str
    family: str          # "proteomic" | "epigenetic"
    target: str          # "chronological" | "mortality"
    trained_on: str      # "general" | "fibrosis"
    analog_of: str
    features: np.ndarray  # indices into the modality's features
    mu: np.ndarray
    sd: np.ndarray
    coef: np.ndarray
    intercept: float

    def predict(self, x: np.ndarray) -> np.ndarray:
        z = (x[:, self.features] - self.mu) / self.sd
        return z @ self.coef + self.intercept


def _ridge(x, y, lam):
    mu, sd = x.mean(0), x.std(0) + 1e-9
    z = (x - mu) / sd
    coef = np.linalg.solve(z.T @ z + lam * np.eye(z.shape[1]), z.T @ (y - y.mean()))
    return mu, sd, coef, float(y.mean())


SPECS = (
    # name, family, target, trained_on, analog_of, feature set
    ("prot_chrono", "proteomic", "chronological", "general", "ProtAge (chronological)", "all"),
    ("organ_chrono", "proteomic", "chronological", "general", "OrganAge, chronological variant", "organ"),
    ("organ_mortality", "proteomic", "mortality", "general", "OrganAge, mortality variant", "organ"),
    ("prot_mortality", "proteomic", "mortality", "general", "PAC (mortality)", "all"),
    ("fibrosis_chrono", "proteomic", "chronological", "fibrosis", "ipfP3GPT (assumed trained in fibrosis)", "all"),
    ("sparse_chrono", "proteomic", "chronological", "general", "PAOPAC (chronological)", "sparse"),
    ("epi_chrono", "epigenetic", "chronological", "general", "first-generation methylation clock", "all"),
    ("epi_mortality", "epigenetic", "mortality", "general", "second-generation methylation clock", "all"),
)
CLOCK_NAMES = tuple(s[0] for s in SPECS)
PROTEOMIC = tuple(s[0] for s in SPECS if s[1] == "proteomic")
EPIGENETIC = tuple(s[0] for s in SPECS if s[1] == "epigenetic")


@lru_cache(maxsize=1)
def clocks() -> dict[str, Clock]:
    rng = np.random.default_rng(20261118)
    ref = sample_cohort(rng, 3000, (20.0, 90.0))
    fib = sample_cohort(rng, 800, (45.0, 85.0), disease="fibrosis")
    data = {"general": (ref, proteome(ref, rng), methylome(ref, rng)),
            "fibrosis": (fib, proteome(fib, rng), methylome(fib, rng))}
    out = {}
    for name, family, target, cohort_name, analog, feats in SPECS:
        c, xp, xm = data[cohort_name]
        x = xp if family == "proteomic" else xm
        y = c.chrono if target == "chronological" else c.mortality_age
        if target == "mortality":  # risk the blood cannot see (lifestyle, genetics, luck)
            y = y + rng.normal(0, 4.0, len(y))
        if feats == "all":
            idx = np.arange(x.shape[1])
        elif feats == "organ":
            idx = np.flatnonzero(PANEL.organ_protein_mask)
        else:  # sparse: top 30 by absolute correlation with the target
            r = np.abs([np.corrcoef(x[:, j], y)[0, 1] for j in range(x.shape[1])])
            idx = np.sort(np.argsort(r)[-30:])
        mu, sd, coef, b = _ridge(x[:, idx], y, lam=50.0)
        out[name] = Clock(name, family, target, cohort_name, analog, idx, mu, sd, coef, b)
    return out


def read_clocks(xp: np.ndarray, xm: np.ndarray, names=CLOCK_NAMES) -> dict[str, np.ndarray]:
    cs = clocks()
    return {n: cs[n].predict(xp if cs[n].family == "proteomic" else xm) for n in names}


def clock_table() -> list[dict]:
    """Held-out accuracy of every clock (healthy test cohort), for the README."""
    rng = np.random.default_rng(99)
    c = sample_cohort(rng, 2000, (20.0, 90.0))
    preds = read_clocks(proteome(c, rng), methylome(c, rng))
    rows = []
    for name, cl in clocks().items():
        y = c.chrono if cl.target == "chronological" else c.mortality_age
        p = preds[name]
        rows.append({"clock": name, "family": cl.family, "target": cl.target, "trained_on": cl.trained_on,
                     "analog_of": cl.analog_of, "n_features": int(len(cl.features)),
                     "r": float(np.corrcoef(p, y)[0, 1]), "mae_years": float(np.mean(np.abs(p - y)))})
    return rows
