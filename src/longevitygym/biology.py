"""Simulated people: organ ages, inflammation, disease, blood cell mix, and the omics they emit.

Ground truth is defined here and nowhere else. Biological age = the mean of seven organ ages.
Inflammation, disease activity and the blood cell mix all move with age and all leak into the
omics, but by definition they are not aging. That definitional line is the whole game: a clock
can drop because the organs got younger, or because something that travels with age moved.
Every number below is an assumed default (docs/ASSUMPTIONS.md), not a measurement.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ORGANS = ("immune", "liver", "kidney", "vascular", "lung", "brain", "muscle")
MORTALITY_WEIGHTS = np.array([1.5, 1.0, 1.3, 1.5, 1.0, 0.8, 0.9])
MORTALITY_WEIGHTS = MORTALITY_WEIGHTS / MORTALITY_WEIGHTS.sum()

N_ORGAN_PROT, N_INFLAM_PROT, N_DISEASE_PROT, N_NOISE_PROT = 25, 20, 20, 25
N_AGE_CPG, N_MIX_CPG, N_NOISE_CPG = 120, 40, 40
N_PROT = len(ORGANS) * N_ORGAN_PROT + N_INFLAM_PROT + N_DISEASE_PROT + N_NOISE_PROT
N_CPG = N_AGE_CPG + N_MIX_CPG + N_NOISE_CPG


@dataclass(frozen=True)
class Panel:
    """Fixed loadings of every protein and CpG. One panel for the whole package (seeded)."""
    prot_organ: np.ndarray      # index into ORGANS, or -1
    prot_age_w: np.ndarray
    prot_inflam_w: np.ndarray
    prot_disease_w: np.ndarray
    cpg_age_w: np.ndarray
    cpg_mix_w: np.ndarray

    @property
    def organ_protein_mask(self) -> np.ndarray:
        return self.prot_organ >= 0


def _signed(rng, lo, hi, n):
    return rng.uniform(lo, hi, n) * rng.choice([-1.0, 1.0], n)


def build_panel(seed: int = 7) -> Panel:
    rng = np.random.default_rng(seed)
    organ = np.concatenate([np.full(N_ORGAN_PROT, k) for k in range(len(ORGANS))]
                           + [np.full(N_INFLAM_PROT + N_DISEASE_PROT + N_NOISE_PROT, -1)])
    n_org = len(ORGANS) * N_ORGAN_PROT
    age_w = np.zeros(N_PROT)
    age_w[:n_org] = _signed(rng, 0.3, 1.0, n_org)
    inflam_w = rng.normal(0, 0.1, N_PROT)
    inflam_w[n_org:n_org + N_INFLAM_PROT] = rng.uniform(0.6, 1.0, N_INFLAM_PROT)
    disease_w = rng.normal(0, 0.05, N_PROT)
    d0 = n_org + N_INFLAM_PROT
    disease_w[d0:d0 + N_DISEASE_PROT] = rng.uniform(0.6, 1.2, N_DISEASE_PROT)
    # lung proteins carry a little disease signal too (fibrotic lung looks older)
    lung = ORGANS.index("lung")
    disease_w[organ == lung] += rng.uniform(0.0, 0.3, N_ORGAN_PROT)
    cpg_age = np.zeros(N_CPG)
    cpg_age[:N_AGE_CPG] = _signed(rng, 0.3, 1.0, N_AGE_CPG)
    cpg_mix = np.zeros(N_CPG)
    cpg_mix[N_AGE_CPG:N_AGE_CPG + N_MIX_CPG] = _signed(rng, 0.5, 1.0, N_MIX_CPG)
    cpg_mix[:N_AGE_CPG] += rng.normal(0, 0.1, N_AGE_CPG)
    return Panel(organ, age_w, inflam_w, disease_w, cpg_age, cpg_mix)


PANEL = build_panel()


@dataclass
class Cohort:
    """Latent state of n people at one moment. Arrays are length n (organ_age is n x 7)."""
    chrono: np.ndarray
    organ_age: np.ndarray
    inflam: np.ndarray
    disease: np.ndarray
    mix: np.ndarray            # blood cell mix axis (lymphoid high, myeloid low), shifts with age
    prot_person: np.ndarray    # stable person-specific protein offsets
    cpg_person: np.ndarray

    @property
    def n(self) -> int:
        return len(self.chrono)

    @property
    def bio_age(self) -> np.ndarray:
        return self.organ_age.mean(axis=1)

    @property
    def mortality_age(self) -> np.ndarray:
        """Target for mortality-trained clocks: organ gaps weighted, plus inflammation and disease."""
        gap = (self.organ_age - self.chrono[:, None]) @ MORTALITY_WEIGHTS
        return self.chrono + 1.2 * gap + 1.5 * self.inflam + 3.0 * self.disease


def sample_cohort(rng: np.random.Generator, n: int, age_range=(45.0, 80.0), disease: str = "none") -> Cohort:
    chrono = rng.uniform(*age_range, n)
    shared = rng.normal(0, 4.0, n)
    organ_age = chrono[:, None] + shared[:, None] + rng.normal(0, 3.0, (n, len(ORGANS)))
    inflam = 0.03 * (chrono - 60) + 0.08 * shared + rng.normal(0, 1.0, n)
    if disease == "fibrosis":
        dis = np.clip(0.8 + 0.02 * (chrono - 60) + rng.normal(0, 0.3, n), 0.1, None)
        organ_age[:, ORGANS.index("lung")] += 4.0 * dis
        inflam = inflam + 0.5 * dis
    elif disease == "none":
        dis = np.zeros(n)
    else:
        raise ValueError(f"unknown disease {disease!r}")
    mix = -0.05 * (chrono - 60) + rng.normal(0, 1.0, n)
    return Cohort(chrono, organ_age, inflam, dis, mix,
                  rng.normal(0, 0.5, (n, N_PROT)), rng.normal(0, 0.4, (n, N_CPG)))


def proteome(c: Cohort, rng: np.random.Generator, batch_shift: np.ndarray | None = None) -> np.ndarray:
    p = PANEL
    org_age = np.where(p.prot_organ >= 0, c.organ_age[:, np.clip(p.prot_organ, 0, None)], 60.0)
    x = (p.prot_age_w * (org_age - 60) / 10 + np.outer(c.inflam, p.prot_inflam_w)
         + np.outer(c.disease, p.prot_disease_w) + c.prot_person + rng.normal(0, 0.3, (c.n, N_PROT)))
    return x if batch_shift is None else x + batch_shift


def methylome(c: Cohort, rng: np.random.Generator, batch_shift: np.ndarray | None = None,
              epi_direct: np.ndarray | None = None) -> np.ndarray:
    """epi_direct: years by which an intervention rewinds the methylation readout itself (n,)."""
    p = PANEL
    sys_age = c.bio_age + (0 if epi_direct is None else epi_direct)
    x = (np.outer((sys_age - 60) / 10, p.cpg_age_w) + np.outer(c.mix, p.cpg_mix_w)
         + c.cpg_person + rng.normal(0, 0.25, (c.n, N_CPG)))
    return x if batch_shift is None else x + batch_shift
