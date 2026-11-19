"""realcheck.py: the calibrated noise profile against the real aggregate targets."""
from longevityrl import make
from longevityrl.clocks import CLOCK_NAMES


def test_calibrated_noise_matches_the_real_targets_and_changes_nothing_else():
    from longevityrl.realcheck import ANALOG, REAL, change_sd, target_change_sd
    default, calibrated, target = change_sd("default", range(3)), change_sd("calibrated", range(3)), target_change_sd()
    for name in CLOCK_NAMES:
        assert default[name] < 0.6 * target[name], name                    # the simulator's own noise is far lower
        assert abs(calibrated[name] - target[name]) < 0.12 * target[name], name
    for name, real in ANALOG.items():
        assert target[name] == REAL["change_sd"][real]["estimate"]
    plain, noisy = make(seed=4), make(seed=4, noise="calibrated")
    assert plain.truth() == noisy.truth() and plain.code == noisy.code
    rows = lambda env: env.step({"n_per_arm": 8})[0]["rows"]
    a, b = rows(plain), rows(noisy)
    assert [r["age"] for r in a] == [r["age"] for r in b] and a != b            # same people, noisier readings
