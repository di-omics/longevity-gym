"""Eight simulated aging clocks: ridge regressions fitted to simulated people from biology.py.

Nothing here is a real clock. No published model, weight, protein list or dataset is used.

The six proteomic clocks borrow one thing each from the six clocks applied in reference [1] of
the README: the training recipe as far as a small linear simulator can express it. That means
what is predicted (chronological age, or a mortality-risk score), who it is fitted on (a mostly
healthy general population for all six, as in [1]), which inputs are used, and that each clock
is fitted on its own subsample of one shared resource. Model class is NOT copied: the originals
are gradient-boosted trees, elastic nets, a Cox and a Gompertz model and a neural network; all
eight here are linear.

    prot_sparse_chrono     recipe from ProtAge [2]: chronological age, a short selected list
    prot_dense_chrono      recipe from the conventional chronological model of [3]
                           (called OrganAge_chrono in [1]): chronological age, whole panel,
                           with the weakest fifth of the features dropped (the original is an
                           elastic net that keeps about four in five proteins)
    prot_sparse_mortality  recipe from the conventional mortality model of [3]
                           (OrganAge_mortality in [1]): mortality, sparse fit from the whole panel
    prot_age_mortality     recipe from PAC [4]: mortality, chronological age plus selected proteins
    prot_dense_chrono_b    recipe from the clock that [1] calls ipfP3GPT, described in [5] as a
                           pathway-aware proteomic aging clock (in [5] the name ipf-P3GPT
                           belongs to a separate transformer): chronological age, every protein
                           kept. The original is a neural network with a branch for
                           fibrosis-related pathways, trained on UK Biobank data. That design
                           is not modelled, so this is a second whole-panel fit on a different
                           subsample and behaves much like prot_dense_chrono.
    prot_organ_chrono      recipe from PAOPAC [6], a family of one conventional clock and 14
                           organ proxy clocks: chronological age, proteins drawn from
                           organ-enriched panels. [1] does not say which PAOPAC model it ran;
                           if it was the conventional one, this imitates the family's organ
                           proxy recipe and not the model that was run.

Every clock also has a calibration card (clock_cards): what an analyst is told about it. The
card is measured in simulated healthy people and says nothing about fibrosis.

Two methylation clocks (chronological and mortality) are this repo's addition. The study in [1]
used proteomic clocks only.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache

import numpy as np

from .biology import PANEL, ORGANS, methylome, proteome, sample_cohort

POOL_N = 40000          # one shared resource, as the six originals share one biobank
SUBSAMPLE = 0.8         # each clock is fitted on its own 80 percent of it
TRAIN_AGES = (40.0, 70.0)
RISK_NOISE_SD = 4.0     # mortality risk the omics cannot see (lifestyle, genetics, luck)
TRAIN_SEED = 20261118


@dataclass(frozen=True)
class Clock:
    name: str
    family: str           # "proteomic" | "epigenetic"
    target: str           # "chronological" | "mortality"
    inputs: str           # plain description of the inputs, shown to the agent
    recipe_from: str      # which published clock the recipe is borrowed from (README only)
    uses_age: bool
    features: np.ndarray  # indices into the modality's features
    mu: np.ndarray
    sd: np.ndarray
    coef: np.ndarray
    intercept: float

    def predict(self, x: np.ndarray, age: np.ndarray | None = None) -> np.ndarray:
        d = x[:, self.features]
        if self.uses_age:
            d = np.column_stack([age, d])
        return ((d - self.mu) / self.sd) @ self.coef + self.intercept


# name, family, target, selection, uses_age, inputs (agent-facing), recipe_from (README only)
SPECS = (
    ("prot_sparse_chrono", "proteomic", "chronological", ("marginal", 17), False,
     "17 proteins selected for their correlation with age", "ProtAge [2]"),
    ("prot_dense_chrono", "proteomic", "chronological", ("pruned", 0), False,
     "the whole panel, weakest fifth of the proteins dropped",
     "conventional chronological model of [3] (OrganAge_chrono in [1])"),
    ("prot_sparse_mortality", "proteomic", "mortality", ("stepwise", 12), False,
     "12 proteins selected stepwise from the whole panel",
     "conventional mortality model of [3] (OrganAge_mortality in [1])"),
    ("prot_age_mortality", "proteomic", "mortality", ("stepwise", 11), True,
     "chronological age plus 11 proteins selected stepwise", "PAC [4]"),
    ("prot_dense_chrono_b", "proteomic", "chronological", ("all", 0), False,
     "all 240 proteins", "ipfP3GPT [5]"),
    ("prot_organ_chrono", "proteomic", "chronological", ("organ_panel", 16), False,
     "16 proteins drawn from organ-enriched panels", "PAOPAC [6]"),
    ("epi_chrono", "epigenetic", "chronological", ("all", 0), False,
     "all 200 methylation sites", "none (this repo's addition)"),
    ("epi_mortality", "epigenetic", "mortality", ("all", 0), False,
     "all 200 methylation sites", "none (this repo's addition)"),
)
CLOCK_NAMES = tuple(s[0] for s in SPECS)
PROTEOMIC = tuple(s[0] for s in SPECS if s[1] == "proteomic")
EPIGENETIC = tuple(s[0] for s in SPECS if s[1] == "epigenetic")


def _zscore(d):
    mu, sd = d.mean(0), d.std(0) + 1e-9
    return mu, sd, (d - mu) / sd


def _stepwise(z, yc, k, forced=()):
    """Forward selection on the residual (a simple stand-in for an L1 penalty)."""
    n = len(yc)
    gram, b = z.T @ z / n, z.T @ yc / n
    chosen = list(forced)
    while len(chosen) < k + len(forced):
        if chosen:
            coef = np.linalg.solve(gram[np.ix_(chosen, chosen)], b[chosen])
            resid = b - gram[:, chosen] @ coef
        else:
            resid = b.copy()
        resid[chosen] = 0.0
        chosen.append(int(np.argmax(np.abs(resid))))
    return chosen


def _select(kind, k, x, y, uses_age, age):
    """Indices of the modality's features that the clock uses."""
    if kind == "all":
        return np.arange(x.shape[1])
    _, _, z = _zscore(x)
    yc = y - y.mean()
    if kind == "pruned":   # fit on everything, then keep the strongest four fifths
        coef = np.linalg.solve(z.T @ z + np.eye(z.shape[1]), z.T @ yc)
        return np.sort(np.argsort(np.abs(coef))[x.shape[1] // 5:])
    corr = np.abs(z.T @ yc / len(yc)) / (y.std() + 1e-9)
    if kind == "marginal":
        return np.sort(np.argsort(corr)[-k:])
    if kind == "stepwise":
        if uses_age:
            _, _, za = _zscore(np.column_stack([age, x]))
            picked = _stepwise(za, yc, k, forced=(0,))
            return np.sort(np.array(picked[1:]) - 1)
        return np.sort(np.array(_stepwise(z, yc, k)))
    if kind == "organ_panel":
        chosen = []
        for organ in range(len(ORGANS)):
            cols = np.flatnonzero(PANEL.prot_organ == organ)
            chosen += list(cols[np.argsort(corr[cols])[-2:]])
        rest = [j for j in np.flatnonzero(PANEL.organ_protein_mask) if j not in chosen]
        rest = sorted(rest, key=lambda j: corr[j])
        rest = rest[len(rest) - (k - len(chosen)):]
        return np.sort(np.array(chosen + rest))
    raise ValueError(kind)


def train_clocks(seed: int = TRAIN_SEED, population: str = "general") -> dict[str, Clock]:
    """population: "general" (mostly healthy, 4 percent with some fibrosis activity; the default)
    or "none" (healthy people only; used by a test to show what the diseased few change)."""
    rng = np.random.default_rng(seed)
    pool = sample_cohort(rng, POOL_N, TRAIN_AGES, disease=population)
    xp, xm = proteome(pool, rng), methylome(pool, rng)
    risk = pool.mortality_age + rng.normal(0, RISK_NOISE_SD, pool.n)
    out = {}
    for name, family, target, (kind, k), uses_age, inputs, recipe in SPECS:
        rows = np.sort(rng.permutation(pool.n)[: int(SUBSAMPLE * pool.n)])
        x = (xp if family == "proteomic" else xm)[rows]
        y = (pool.chrono if target == "chronological" else risk)[rows]
        age = pool.chrono[rows]
        idx = _select(kind, k, x, y, uses_age, age)
        d = np.column_stack([age, x[:, idx]]) if uses_age else x[:, idx]
        mu, sd, z = _zscore(d)
        coef = np.linalg.solve(z.T @ z + 1.0 * np.eye(z.shape[1]), z.T @ (y - y.mean()))
        out[name] = Clock(name, family, target, inputs, recipe, uses_age, idx, mu, sd, coef, float(y.mean()))
    return out


@lru_cache(maxsize=1)
def clocks() -> dict[str, Clock]:
    return train_clocks()


def read_clocks(xp: np.ndarray, xm: np.ndarray, age: np.ndarray, names=CLOCK_NAMES, fitted=None) -> dict:
    cs = fitted or clocks()
    return {n: cs[n].predict(xp if cs[n].family == "proteomic" else xm, age) for n in names}


def _read_cohort(c, seed, fitted=None, epi_direct=None):
    """Clock readings for a cohort with a fixed noise seed, so two calls differ only by the latent state."""
    rng = np.random.default_rng(seed)
    return read_clocks(proteome(c, rng), methylome(c, rng, epi_direct=epi_direct), c.chrono, fitted=fitted)


def clock_table(fitted=None) -> list[dict]:
    """Held-out accuracy of every clock and what each one reads besides aging.

    Accuracy: a fresh simulated general population (not the training pool). Chronological clocks
    are scored against chronological age; mortality clocks against the noisy mortality-risk score
    they were trained on. Sensitivities: the change in the clock's reading, in years, when one
    hidden quantity is moved in healthy people and everything else (noise included) is held fixed.
    """
    cs = fitted or clocks()
    rng = np.random.default_rng(99)
    c = sample_cohort(rng, 10000, TRAIN_AGES, disease="general")
    risk = c.mortality_age + rng.normal(0, RISK_NOISE_SD, c.n)
    preds = read_clocks(proteome(c, rng), methylome(c, rng), c.chrono, fitted=cs)
    h = sample_cohort(np.random.default_rng(98), 2000, TRAIN_AGES, disease="none")
    base = _read_cohort(h, 5, cs)
    moved = {
        "per_year_organ_aging": _read_cohort(replace(h, organ_age=h.organ_age + 1.0), 5, cs),
        "per_sd_inflammation": _read_cohort(replace(h, inflam=h.inflam + 1.0), 5, cs),
        "per_unit_fibrosis": _read_cohort(replace(h, disease=h.disease + 1.0), 5, cs),
        "per_sd_cell_mix": _read_cohort(replace(h, mix=h.mix + 1.0), 5, cs),
    }
    rows = []
    for name, cl in cs.items():
        y = c.chrono if cl.target == "chronological" else risk
        p = preds[name]
        row = {"clock": name, "family": cl.family, "target": cl.target, "inputs": cl.inputs,
               "recipe_from": cl.recipe_from, "r": float(np.corrcoef(p, y)[0, 1]),
               "mae_years": float(np.mean(np.abs(p - y)))}
        row.update({k: float(np.mean(v[name] - base[name])) for k, v in moved.items()})
        rows.append(row)
    return rows


@lru_cache(maxsize=1)
def clock_cards() -> dict:
    """What an analyst is told about each clock: how far its reading moves per year of true organ
    aging and per unit of the two measurable covariates, from validation in simulated healthy
    people. Its reading of fibrosis activity is deliberately not on the card: in this toy world,
    as in the study behind it, the clocks were never characterised in patients."""
    return {r["clock"]: {"years_per_year_of_aging": round(r["per_year_organ_aging"], 2),
                         "years_per_sd_cell_mix": round(r["per_sd_cell_mix"], 2),
                         "years_per_sd_inflammation": round(r["per_sd_inflammation"], 2)}
            for r in clock_table()}


TABLE_CAPTION = (
    "All eight rows are ridge regressions on simulated features. None is a real clock. The fourth column names "
    "the published clock whose training recipe the row imitates; no published model, weight or protein list is "
    "used. r and MAE are measured on held-out simulated people and are not accuracy figures for any published "
    "clock. Numbers in square brackets refer to the reference list in README.md.")


def clock_table_markdown(fitted=None) -> str:
    out = ["# The eight simulated clocks", "", TABLE_CAPTION, "",
           "| clock | target | inputs | recipe borrowed from (not the model) | r | MAE (yr) "
           "| per year of organ aging | per SD inflammation | per unit fibrosis activity | per SD cell mix |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in clock_table(fitted):
        out.append(f"| {r['clock']} | {r['target']} | {r['inputs']} | {r['recipe_from']} | {r['r']:.2f} | "
                   f"{r['mae_years']:.1f} | {r['per_year_organ_aging']:+.2f} | {r['per_sd_inflammation']:+.2f} | "
                   f"{r['per_unit_fibrosis']:+.2f} | {r['per_sd_cell_mix']:+.2f} |")
    return "\n".join(out) + "\n"


SENSITIVITIES = ("per_year_organ_aging", "per_sd_inflammation", "per_unit_fibrosis", "per_sd_cell_mix")


def seed_check_markdown(seeds=(1, 2, 3, 4, 5)) -> str:
    """Refit the clocks with other training seeds and report the range of each sensitivity."""
    tables = [clock_table(train_clocks(seed)) for seed in seeds]
    shared = np.flatnonzero(PANEL.prot_kind == 2)
    counts = {name: [] for name in CLOCK_NAMES}
    for seed in seeds:
        for name, cl in train_clocks(seed).items():
            counts[name].append(int(np.isin(cl.features, shared).sum()) if cl.family == "proteomic" else 0)
    out = ["# Do the clock sensitivities depend on the training seed?", "",
           f"Each clock refitted with training seeds {', '.join(str(s) for s in seeds)}. Cells give the lowest and "
           "highest value over those refits, in years. Last column: how many of the four shared proteins the "
           "clock uses.", "",
           "| clock | per year of organ aging | per SD inflammation | per unit fibrosis activity | per SD cell mix "
           "| shared proteins used |", "|---|---|---|---|---|---|"]
    for i, name in enumerate(CLOCK_NAMES):
        cells = []
        for key in SENSITIVITIES:
            vals = [t[i][key] for t in tables]
            cells.append(f"{min(vals):+.2f} to {max(vals):+.2f}")
        used = counts[name]
        cells.append(f"{min(used)} to {max(used)}" if min(used) != max(used) else f"{used[0]}")
        out.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"
