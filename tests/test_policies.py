"""policies.py: the scripted reference against the named mistakes."""
import numpy as np

from longevitygym import make
from longevitygym.policies import POLICIES, run_episode


def test_reference_beats_the_named_mistakes_on_average():
    seeds = range(60)
    mean = lambda p: float(np.mean([run_episode(make(seed=s), POLICIES[p])[0] for s in seeds]))
    reference = mean("reference")
    assert reference > 0.75
    for p in ("always_no", "always_yes", "no_placebo", "plates_by_arm", "cherry_pick_best_clock", "short_trial_4wk"):
        assert reference - mean(p) > 0.1, p
