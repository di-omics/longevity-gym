"""Longevity RL: compare reporting policies on identical simulated clock trials.

Study design is fixed. The model-based policy uses nearby training trials as an
empirical model of the hidden outcome given the observed clock changes. It chooses
a single terminal report. There is no multi-round trial planning or human evidence.
"""
from __future__ import annotations

from copy import deepcopy

import numpy as np

from .clocks import EPIGENETIC, PROTEOMIC
from .env import NOISE_PROFILES, make
from .envqc import paired
from .policies import POLICIES, REFERENCE_DESIGN, calibrated_effects, report


SCRIPTED = ("reference", "always_no", "average_all_clocks")


def _trial(seed, noise):
    env = make("clock_trial", seed=seed, noise=noise)
    spec = env.reset()
    observation, _, _, _ = env.step(REFERENCE_DESIGN)
    return env, spec, observation


def _clock_medians(spec, observation):
    effects = calibrated_effects(spec, observation, REFERENCE_DESIGN["clocks"])
    return [np.median([effects[name] for name in family]) for family in (PROTEOMIC, EPIGENETIC)]


def _score_report(env, action):
    # Every counterfactual report starts from exactly the same post-design state.
    _, reward, _, info = deepcopy(env).step(action)
    return reward, info


def _fit_outcome_model(seeds, noise):
    features, outcomes, simulations = [], [], []
    for seed in seeds:
        env, spec, observation = _trial(seed, noise)
        features.append(_clock_medians(spec, observation))
        _, result = _score_report(env, report(0.0))
        outcomes.append(result["true_effect_years"])
        simulations.append(env)

    features = np.asarray(features)
    scale = features.std(axis=0)
    scale[scale == 0] = 1.0

    def policy(spec, observation):
        distance = np.sum(((_clock_medians(spec, observation) - features) / scale) ** 2, axis=1)
        neighbours = np.argsort(distance, kind="stable")[:8]
        # Uniform empirical posterior over these completed training trials. Test
        # the observed-effect reports and the null against its simulated rewards.
        candidates = [report(0.0)] + [report(outcomes[i]) for i in neighbours]
        return max(candidates, key=lambda action: sum(
            _score_report(simulations[i], action)[0] for i in neighbours))

    return policy


def run_benchmark(*, train_seeds: int = 32, test_seeds: int = 16,
                  seed: int = 0, noise: str = "default") -> dict:
    """Fit on contiguous training seeds, then evaluate on the following unseen seeds.

    The seed counts are positive. Both sets use the requested noise profile.
    Returned paired differences are policy reward minus reference reward.
    """
    for name, value, minimum in (("train_seeds", train_seeds, 1), ("test_seeds", test_seeds, 1),
                                 ("seed", seed, 0)):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
            raise ValueError(f"{name} must be an integer of at least {minimum}")
    if noise not in NOISE_PROFILES:
        raise ValueError(f"noise must be one of {NOISE_PROFILES}")

    first, n_train, n_test = int(seed), int(train_seeds), int(test_seeds)
    train_ids = list(range(first, first + n_train))
    test_ids = list(range(first + n_train, first + n_train + n_test))
    policies = {name: POLICIES[name] for name in SCRIPTED}
    policies["model_based"] = _fit_outcome_model(train_ids, noise)
    episodes = []
    for test_seed in test_ids:
        env, spec, observation = _trial(test_seed, noise)
        # Make every decision before any held-out truth is released for scoring.
        decisions = {name: policy(spec, observation) for name, policy in policies.items()}
        results = {}
        for name, action in decisions.items():
            reward, info = _score_report(env, action)
            results[name] = {"estimate": info["estimate"], "call": info["call"], "reward": reward,
                             "abs_error": info["abs_error"], "call_correct": info["call_correct"]}
        episodes.append({"seed": test_seed, "true_effect_years": info["true_effect_years"],
                         "geroprotective": info["geroprotective"], "cost": info["cost"],
                         "policies": results})

    summary = {}
    reference = np.array([row["policies"]["reference"]["reward"] for row in episodes])
    for name in policies:
        rows = [row["policies"][name] for row in episodes]
        rewards = np.array([row["reward"] for row in rows])
        comparison = paired(rewards, reference)
        summary[name] = {
            "mean_reward": float(np.mean(rewards)),
            "call_accuracy": float(np.mean([row["call_correct"] for row in rows])),
            "mean_abs_error_years": float(np.mean([row["abs_error"] for row in rows])),
            "mean_paired_reward_vs_reference": comparison["gap"],
            "paired_reward_se": comparison["se"] if n_test > 1 else None,
        }
    return {"name": "Longevity RL", "source": "synthetic", "noise": noise, "seed": first,
            "design": deepcopy(REFERENCE_DESIGN), "train_seeds": train_ids, "test_seeds": test_ids,
            "policies": summary, "episodes": episodes}
