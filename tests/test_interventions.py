"""interventions.py: what each archetype does to the clocks, next to the simulated truth."""
import numpy as np

from longevitygym import make
from longevitygym.clocks import CLOCK_NAMES, EPIGENETIC, PROTEOMIC
from longevitygym.policies import REFERENCE_DESIGN, clock_effect


def _trial(intervention, cohort, seeds=(3, 4, 5, 6), dose=2, n=150):
    """Mean clock readings over a few large simulated trials at nominal potency, and the truth."""
    per = {c: [] for c in CLOCK_NAMES}
    for seed in seeds:
        env = make(seed=seed, intervention=intervention, cohort=cohort, dose=dose, potency=(1.0, 1.0))
        env.reset()
        obs, *_ = env.step({**REFERENCE_DESIGN, "n_per_arm": n})
        for c in CLOCK_NAMES:
            per[c].append(clock_effect(obs["rows"], c, 26))
    return {c: float(np.mean(v)) for c, v in per.items()}, env.truth()["true_effect_years"]


def test_antifibrotic_moves_every_proteomic_clock_but_not_the_organs():
    est, truth = _trial("antifibrotic", "fibrosis")
    assert -0.2 < truth < 0
    for name in PROTEOMIC:
        assert est[name] < truth - 0.05, name
    assert np.median([est[n] for n in PROTEOMIC]) < -0.5      # a proteomics-only reading calls it geroprotective
    for name in EPIGENETIC:
        assert abs(est[name] - truth) < 0.3, name
    healthy, truth_h = _trial("antifibrotic", "healthy")
    assert truth_h == 0.0 and max(abs(v) for v in healthy.values()) < 0.3


def test_methylation_clocks_overread_reprogramming_and_proteomic_ones_do_not():
    est, truth = _trial("reprogramming_like", "healthy")
    for name in EPIGENETIC:
        assert est[name] < truth - 3, name
    for name in PROTEOMIC:
        assert abs(est[name] - truth) < 0.4, name


def test_cell_mix_shift_moves_only_the_chronological_methylation_clock():
    est, truth = _trial("immune_mobilizer", "healthy")
    assert truth == 0.0 and est["epi_chrono"] < -0.8
    for name in PROTEOMIC:
        assert abs(est[name]) < 0.3, name
