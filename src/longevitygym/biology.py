"""Simulated people: organ ages, inflammation, fibrosis activity, blood cell mix, and the omics they emit.

Ground truth is defined here and nowhere else. Biological age = the mean of seven organ ages.
Inflammation, fibrosis activity and the blood cell mix all leak into the omics, but by this
package's definition they are not aging. That definitional line is the whole game: a clock can
drop because the organs got younger, or because something else that the clock reads has moved.

One mechanism is taken from the study that motivates the repo (README, reference [1]): a
fibrosis-related protein was the most important feature there and the only important one shared
by all six clocks. Here four lung-enriched "shared" proteins are the strongest and least noisy
age markers in healthy people and also rise with fibrosis activity, so every clock trained in
healthy people leans on them, and a treatment that lowers fibrosis activity lowers them.

Every number below is an assumed default (docs/ASSUMPTIONS.md), not a measurement. The features
are unnamed simulated numbers, not real proteins or CpG sites.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ORGANS = ("immune", "liver", "kidney", "vascular", "lung", "brain", "muscle")
MORTALITY_WEIGHTS = np.array([1.5, 1.0, 1.3, 1.5, 1.0, 0.8, 0.9])
MORTALITY_WEIGHTS = MORTALITY_WEIGHTS / MORTALITY_WEIGHTS.sum()

N_ORGAN_PROT, N_INFLAM_PROT, N_DISEASE_PROT, N_NOISE_PROT = 25, 20, 12, 33
N_SHARED_PROT = 4   # the first four lung-enriched proteins
N_AGE_CPG, N_MIX_CPG, N_NOISE_CPG = 120, 40, 40
N_PROT = len(ORGANS) * N_ORGAN_PROT + N_INFLAM_PROT + N_DISEASE_PROT + N_NOISE_PROT
N_CPG = N_AGE_CPG + N_MIX_CPG + N_NOISE_CPG
KIND_ORGAN, KIND_INFLAM, KIND_SHARED, KIND_DISEASE, KIND_NOISE = range(5)
KIND_NAMES = ("organ-enriched", "inflammation", "shared (lung-enriched, age and fibrosis)", "fibrosis only",
              "uninformative")


@dataclass(frozen=True)
class Panel:
    """Fixed loadings of every simulated protein and methylation site. One panel for the package."""
    prot_organ: np.ndarray     # organ index for organ-enriched proteins (shared ones included), else -1
    prot_kind: np.ndarray      # KIND_* per protein
    prot_age_w: np.ndarray     # per decade of that organ's age
    prot_noise_scale: np.ndarray  # multiplies person offsets and measurement noise (0.3 for shared proteins)
    prot_inflam_w: np.ndarray  # per SD of inflammation
    prot_disease_w: np.ndarray  # per unit of fibrosis activity
    cpg_age_w: np.ndarray      # per decade of mean organ age
    cpg_mix_w: np.ndarray      # per SD of the blood cell mix axis

    @property
    def organ_protein_mask(self) -> np.ndarray:
        return self.prot_organ >= 0


def _signed(rng, lo, hi, n):
    return rng.uniform(lo, hi, n) * rng.choice([-1.0, 1.0], n)


def build_panel(seed: int = 7) -> Panel:
    rng = np.random.default_rng(seed)
    n_org = len(ORGANS) * N_ORGAN_PROT
    organ = np.concatenate([np.full(N_ORGAN_PROT, k) for k in range(len(ORGANS))] + [np.full(N_PROT - n_org, -1)])
    kind = np.concatenate([np.full(n_org, KIND_ORGAN), np.full(N_INFLAM_PROT, KIND_INFLAM),
                           np.full(N_DISEASE_PROT, KIND_DISEASE), np.full(N_NOISE_PROT, KIND_NOISE)])
    lung = np.flatnonzero(organ == ORGANS.index("lung"))
    shared = lung[:N_SHARED_PROT]
    kind[shared] = KIND_SHARED
    age_w = np.zeros(N_PROT)
    age_w[:n_org] = _signed(rng, 0.3, 1.0, n_org)
    age_w[shared] = rng.uniform(1.0, 1.2, N_SHARED_PROT)          # strong age markers, rising with age
    noise_scale = np.ones(N_PROT)
    noise_scale[shared] = 0.3                                     # and far less noisy than the rest
    inflam_w = rng.normal(0, 0.03, N_PROT)                        # small background loading everywhere
    inflam_w[kind == KIND_INFLAM] = rng.uniform(0.6, 1.0, N_INFLAM_PROT)
    disease_w = rng.normal(0, 0.02, N_PROT)
    disease_w[kind == KIND_DISEASE] = rng.uniform(0.6, 1.2, N_DISEASE_PROT)
    disease_w[shared] = rng.uniform(0.6, 1.2, N_SHARED_PROT)      # and rising with fibrosis
    # disease looks like aging across the proteome: every other organ-enriched protein also moves a
    # little in its own "older" direction with fibrosis activity (about one apparent year per unit)
    others = np.flatnonzero((organ >= 0) & (kind == KIND_ORGAN))
    disease_w[others] += np.sign(age_w[others]) * rng.uniform(0.0, 0.15, len(others))
    cpg_age = np.zeros(N_CPG)
    cpg_age[:N_AGE_CPG] = _signed(rng, 0.3, 1.0, N_AGE_CPG)
    cpg_mix = np.zeros(N_CPG)
    cpg_mix[N_AGE_CPG:N_AGE_CPG + N_MIX_CPG] = _signed(rng, 0.5, 1.0, N_MIX_CPG)
    cpg_mix[:N_AGE_CPG] += rng.normal(0, 0.1, N_AGE_CPG)
    return Panel(organ, kind, age_w, noise_scale, inflam_w, disease_w, cpg_age, cpg_mix)


PANEL = build_panel()


@dataclass
class Cohort:
    """Latent state of n people at one moment. Arrays are length n (organ_age is n x 7)."""
    chrono: np.ndarray
    organ_age: np.ndarray
    inflam: np.ndarray
    disease: np.ndarray        # fibrosis activity; 0 in people without the disease
    mix: np.ndarray            # blood cell mix axis (lymphoid high, myeloid low); falls with age
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
        """A made-up mortality-risk score in years (no deaths are simulated): what the mortality
        clocks are asked to predict. Organ gaps count, and so do inflammation and fibrosis."""
        gap = (self.organ_age - self.chrono[:, None]) @ MORTALITY_WEIGHTS
        return self.chrono + 1.2 * gap + 1.5 * self.inflam + 3.0 * self.disease

    def head(self, n: int) -> "Cohort":
        return Cohort(self.chrono[:n], self.organ_age[:n], self.inflam[:n], self.disease[:n], self.mix[:n],
                      self.prot_person[:n], self.cpg_person[:n])


def sample_cohort(rng: np.random.Generator, n: int, age_range=(45.0, 80.0), disease: str = "none") -> Cohort:
    """disease: "none" (healthy), "fibrosis" (everyone has the disease) or "general" (a mostly
    healthy population: 4 percent carry some fibrosis activity)."""
    chrono = rng.uniform(*age_range, n)
    shared = rng.normal(0, 4.0, n)
    organ_age = chrono[:, None] + shared[:, None] + rng.normal(0, 3.0, (n, len(ORGANS)))
    # inflammation tracks biological age: calendar age and the shared offset count equally
    inflam = 0.05 * (chrono - 60) + 0.05 * shared + rng.normal(0, 1.0, n)
    if disease == "fibrosis":
        dis = np.clip(0.8 + 0.02 * (chrono - 60) + rng.normal(0, 0.3, n), 0.1, None)
    elif disease == "general":
        dis = np.where(rng.random(n) < 0.04, rng.uniform(0.2, 1.2, n), 0.0)
    elif disease == "none":
        dis = np.zeros(n)
    else:
        raise ValueError(f"unknown disease {disease!r}")
    inflam = inflam + 0.5 * dis
    mix = -0.05 * (chrono - 60) + rng.normal(0, 1.0, n)
    return Cohort(chrono, organ_age, inflam, dis, mix,
                  rng.normal(0, 0.5, (n, N_PROT)) * PANEL.prot_noise_scale, rng.normal(0, 0.4, (n, N_CPG)))


def proteome(c: Cohort, rng: np.random.Generator, plate_shift: np.ndarray | None = None) -> np.ndarray:
    p = PANEL
    x = c.prot_person + rng.normal(0, 0.3, (c.n, N_PROT)) * p.prot_noise_scale
    for k in range(len(ORGANS)):
        cols = np.flatnonzero(p.prot_organ == k)
        x[:, cols] += np.outer((c.organ_age[:, k] - 60) / 10, p.prot_age_w[cols])
    x += np.outer(c.inflam, p.prot_inflam_w)
    x += np.outer(c.disease, p.prot_disease_w)
    return x if plate_shift is None else x + plate_shift


def methylome(c: Cohort, rng: np.random.Generator, plate_shift: np.ndarray | None = None,
              epi_direct: np.ndarray | None = None) -> np.ndarray:
    """Blood methylation. It reads mean organ age and the cell mix, and in this simulator it does
    not see fibrosis or inflammation at all (an assumption that matters; see the README limits).
    epi_direct: years by which an intervention rewinds the methylation readout itself (n,)."""
    p = PANEL
    sys_age = c.bio_age + (0 if epi_direct is None else epi_direct)
    x = c.cpg_person + rng.normal(0, 0.25, (c.n, N_CPG))
    x += np.outer((sys_age - 60) / 10, p.cpg_age_w)
    x += np.outer(c.mix, p.cpg_mix_w)
    return x if plate_shift is None else x + plate_shift
