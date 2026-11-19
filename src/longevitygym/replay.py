"""A fixed-pool, synthetic two-endpoint bandit for comparing batch decisions.

Every item has two frozen binary observations. Its only visible feature is an
arbitrary group. The reward is one when both observations are positive. The
planner updates a group-level belief and plans at most two batches ahead. This
is model-based planning with an analytic belief update, without weight training.
"""
from __future__ import annotations

import numpy as np


GROUPS = 8
ITEMS_PER_GROUP = 192
POOL_SIZE = GROUPS * ITEMS_PER_GROUP
WELLS = 1536
CONTROLS = 192
WELLS_PER_ITEM = 4
BATCH_CAPACITY = (WELLS - CONTROLS) // WELLS_PER_ITEM
ROLLOUTS = 96
# Categorical outcomes 00, 01, 10, 11. The marginal joint-hit prior is Beta(2, 5).
OUTCOME_PRIOR = np.array([3, 1, 1, 2])
POLICY_NAMES = ("random", "fixed", "active", "planner", "greedy")


def _integer(name, value, minimum):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(f"{name} must be an integer of at least {minimum}")
    return int(value)


def _allocate(scores, remaining, batch_size):
    """Fill in descending score order, also supporting a matrix of rollout scores."""
    order = np.argsort(-scores, axis=-1, kind="stable")
    capacity = remaining[order]
    slots = batch_size - (np.cumsum(capacity, axis=-1) - capacity)
    ordered_counts = np.minimum(capacity, np.maximum(slots, 0))
    counts = np.zeros_like(ordered_counts)
    np.put_along_axis(counts, order, ordered_counts, axis=-1)
    return counts


def _plan(hits, misses, remaining, batch_size, rounds_left, rng):
    """Evaluate exploration and exploitation batches under the current posterior."""
    means = hits / (hits + misses)
    greedy = _allocate(means, remaining, batch_size)
    if rounds_left == 1:
        return greedy

    # Consider exploiting, filling each available group first, or spreading the
    # batch uniformly over the remaining pool. Only these first moves are compared.
    options = [greedy, rng.multivariate_hypergeometric(remaining, batch_size)]
    for group in np.flatnonzero(remaining):
        scores = means.copy()
        scores[group] = 2.0
        options.append(_allocate(scores, remaining, batch_size))

    draws = rng.beta(hits, misses, size=(ROLLOUTS, GROUPS))
    best_value = -np.inf
    best = greedy
    for counts in np.unique(options, axis=0):
        # Sample hypothetical reports from the posterior predictive. All second
        # moves see only the simulated observations, never the sampled true rates.
        reports = rng.binomial(counts, draws)
        updated_means = (hits + reports) / (hits + misses + counts)
        next_batch = _allocate(updated_means, remaining - counts, batch_size)
        value = counts @ means + np.mean(np.sum(next_batch * updated_means, axis=1))
        if value > best_value:
            best, best_value = counts, value
    return best


def _active(hits, misses, remaining, batch_size, rng):
    """One posterior sample per slot distributes a batch by Thompson sampling."""
    sampled = rng.beta(hits, misses, size=(batch_size, GROUPS))
    counts = np.zeros(GROUPS, dtype=int)
    for rates in sampled:
        group = np.argmax(np.where(counts < remaining, rates, -np.inf))
        counts[group] += 1
    return counts


def _run_policy(name, labels, queues, warm_ids, seed, rounds, batch_size):
    # The scorer owns labels. Selection functions receive only counts from
    # revealed observations, available capacities, and their own random stream.
    rng = np.random.default_rng(seed)
    used = np.bincount(warm_ids // ITEMS_PER_GROUP, minlength=GROUPS)
    successes = np.bincount(warm_ids[labels[warm_ids] == 3] // ITEMS_PER_GROUP,
                            minlength=GROUPS)
    hits = successes + OUTCOME_PRIOR[3]
    misses = used - successes + OUTCOME_PRIOR[:3].sum()
    initial_means = hits / (hits + misses)
    cumulative = 0
    trace = []
    for step in range(rounds):
        remaining = ITEMS_PER_GROUP - used
        if name == "random":
            counts = rng.multivariate_hypergeometric(remaining, batch_size)
        elif name == "fixed":
            counts = _allocate(initial_means, remaining, batch_size)
        elif name == "greedy":
            counts = _allocate(hits / (hits + misses), remaining, batch_size)
        elif name == "active":
            counts = _active(hits, misses, remaining, batch_size, rng)
        else:
            counts = _plan(hits, misses, remaining, batch_size, rounds - step, rng)
        selected = np.concatenate([queues[g, used[g]:used[g] + counts[g]]
                                   for g in np.flatnonzero(counts)])
        observed = labels[selected]
        new_hits = np.bincount(selected[observed == 3] // ITEMS_PER_GROUP,
                               minlength=GROUPS)
        used += counts
        hits += new_hits
        misses += counts - new_hits
        joint_hits = int(new_hits.sum())
        cumulative += joint_hits
        trace.append({"round": step + 1, "selected": selected.tolist(),
                      "observed": observed.tolist(), "joint_hits": joint_hits,
                      "cumulative_hits": cumulative})
    return trace


def run_replay(seed: int = 0, rounds: int = 4, batch_size: int = 24, warm_start: int = 8) -> dict:
    """Run all policies on identical synthetic items and starting observations.

    The item ID divided by ITEMS_PER_GROUP identifies its group. Observations use
    two-bit integers (0 through 3). Per-round hit counts exclude the warm start.
    One batch is at most a pair of virtual 1,536-slot plates, one per endpoint.
    """
    seed = _integer("seed", seed, 0)
    rounds = _integer("rounds", rounds, 1)
    batch_size = _integer("batch_size", batch_size, 1)
    warm_start = _integer("warm_start", warm_start, 1)
    if batch_size > BATCH_CAPACITY or warm_start > BATCH_CAPACITY:
        raise ValueError(f"batch_size and warm_start must each fit {BATCH_CAPACITY} paired profiles")
    if warm_start + rounds * batch_size > POOL_SIZE:
        raise ValueError(f"warm start and all rounds must fit the {POOL_SIZE}-item pool")

    world_seed, order_seed, *policy_seeds = np.random.SeedSequence(seed).spawn(2 + len(POLICY_NAMES))
    world_rng = np.random.default_rng(world_seed)
    probabilities = world_rng.dirichlet(OUTCOME_PRIOR, size=GROUPS)
    labels = np.concatenate([world_rng.choice(4, ITEMS_PER_GROUP, p=p) for p in probabilities])
    order_rng = np.random.default_rng(order_seed)
    queues = np.stack([g * ITEMS_PER_GROUP + order_rng.permutation(ITEMS_PER_GROUP)
                       for g in range(GROUPS)])
    # Warm observations are stratified across groups, including at very small budgets.
    warm_ids = queues[order_rng.permutation(GROUPS)].T.ravel()[:warm_start]
    policies = {name: _run_policy(name, labels, queues, warm_ids, stream, rounds, batch_size)
                for name, stream in zip(POLICY_NAMES, policy_seeds)}
    return {"source": "synthetic", "seed": seed, "rounds": rounds, "batch_size": batch_size,
            "pool_size": POOL_SIZE, "warm_ids": warm_ids.tolist(),
            "warm_observed": labels[warm_ids].tolist(),
            "plate_budget": {"plates_per_batch": 2, "wells_per_plate": WELLS,
                             "controls_per_plate": CONTROLS, "wells_per_item_per_endpoint": WELLS_PER_ITEM,
                             "paired_capacity": BATCH_CAPACITY},
            "policies": policies}


def compare_campaigns(*, seed: int = 0, campaigns: int = 100, rounds: int = 4,
                      batch_size: int = 24, warm_start: int = 8) -> dict:
    """Compare end-of-campaign hit counts on the same consecutive seeds for every policy."""
    seed = _integer("seed", seed, 0)
    campaigns = _integer("campaigns", campaigns, 1)
    totals = {name: 0 for name in POLICY_NAMES}
    comparisons = {name: {"wins": 0, "ties": 0, "losses": 0} for name in ("greedy", "active")}
    for campaign_seed in range(seed, seed + campaigns):
        replay = run_replay(campaign_seed, rounds, batch_size, warm_start)
        counts = {name: trace[-1]["cumulative_hits"] for name, trace in replay["policies"].items()}
        for name, count in counts.items():
            totals[name] += count
        for name, record in comparisons.items():
            difference = counts["planner"] - counts[name]
            if difference > 0:
                record["wins"] += 1
            elif difference < 0:
                record["losses"] += 1
            else:
                record["ties"] += 1
    for name, record in comparisons.items():
        record["mean_difference"] = (totals["planner"] - totals[name]) / campaigns
    return {"source": "synthetic", "first_seed": seed, "campaigns": campaigns, "rounds": int(rounds),
            "batch_size": int(batch_size), "warm_start": int(warm_start),
            "mean_hits": {name: total / campaigns for name, total in totals.items()},
            "planner_comparisons": comparisons}
