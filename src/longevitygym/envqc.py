"""Environment QC: does the reward separate the expert from each named mistake? (Same method as drugdev-gym.)"""
from __future__ import annotations

import numpy as np

from .env import make
from .policies import POLICIES, TRAPS, run_episode


def verdict(gap, z, wins):
    if gap < 0 and wins < 0.4:
        return "inverted"
    if gap > 0 and z >= 0.5:
        return "clean"
    if wins >= 0.9:
        return "visible"
    if wins >= 0.6 or gap >= 0.1:
        return "weak"
    return "blind"


def separation(expert, other):
    gap = float(expert.mean() - other.mean())
    spread = expert.std(ddof=1) + other.std(ddof=1)
    z = float(1 - 3 * spread / abs(gap)) if gap != 0 else float("-inf")
    wins = float(np.mean(expert > other) + 0.5 * np.mean(expert == other))
    return {"gap": gap, "zprime": z, "win_rate": wins, "verdict": verdict(gap, z, wins)}


def qc_card(n_seeds=200, first_seed=0) -> dict:
    seeds = range(first_seed, first_seed + n_seeds)
    res, mech = {}, {}
    for name, pol in POLICIES.items():
        r, err, calls, ivs = [], [], [], []
        for s in seeds:
            rew, info = run_episode(make(seed=s), pol)
            r.append(rew); err.append(info["abs_error"]); calls.append(info["call_correct"])
            ivs.append(info["intervention"])
        res[name] = (np.array(r), np.array(err), np.array(calls, float))
        by_iv = {}
        for iv, e in zip(ivs, err):
            by_iv.setdefault(iv, []).append(e)
        mech[name] = {iv: float(np.mean(v)) for iv, v in sorted(by_iv.items())}
    expert = res["expert"][0]
    rows = []
    for name, (r, err, calls) in res.items():
        row = {"policy": name, "mean": float(r.mean()), "sd": float(r.std(ddof=1)),
               "median_abs_error_years": float(np.median(err)), "call_accuracy": float(calls.mean()),
               "mistake": TRAPS.get(name, "")}
        if name != "expert":
            row.update(separation(expert, r))
        rows.append(row)
    return {"env": "clock_trial", "n_seeds": n_seeds, "first_seed": first_seed, "rows": rows,
            "mean_abs_error_by_intervention": mech}


def card_markdown(card) -> str:
    out = [f"# Environment QC: {card['env']}", "",
           f"Seeds {card['first_seed']} to {card['first_seed'] + card['n_seeds'] - 1}, every policy on the same hidden truth.", "",
           "| policy | mistake | mean reward | median error (yr) | call accuracy | win rate of expert | Z' | verdict |",
           "|---|---|---|---|---|---|---|---|"]
    for r in card["rows"]:
        if r["policy"] == "expert":
            tail = "reference | | "
        else:
            z = "n/a" if not np.isfinite(r["zprime"]) else f"{r['zprime']:.2f}"
            tail = f"{100 * r['win_rate']:.0f}% | {z} | {r['verdict']}"
        out.append(f"| {r['policy']} | {r['mistake']} | {r['mean']:.3f} | {r['median_abs_error_years']:.2f} | "
                   f"{100 * r['call_accuracy']:.0f}% | {tail}")
    out += ["", "Verdicts: clean = Z' >= 0.5; visible = expert wins >= 90% of paired seeds; weak = wins 60 to 90% "
            "or mean gap >= 0.1; blind = neither; inverted = the mistake wins.", ""]
    m = card["mean_abs_error_by_intervention"]
    ivs = list(m["expert"])
    out += ["## Where each mistake bites: mean absolute error in years, by hidden intervention", "",
            "| policy | " + " | ".join(ivs) + " |", "|---|" + "---|" * len(ivs)]
    for pol, row in m.items():
        cells = []
        for iv in ivs:
            v = row[iv]
            flag = "**" if pol != "expert" and v - m["expert"][iv] >= 0.3 else ""
            cells.append(f"{flag}{v:.2f}{flag}")
        out.append(f"| {pol} | " + " | ".join(cells) + " |")
    out += ["", "Bold = at least 0.3 years worse than the expert on that intervention.", ""]
    return "\n".join(out)
