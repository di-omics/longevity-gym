"""Environment QC: can the reward tell the reference analysis from each named mistake?

Every policy runs on the same seeds, so the comparison is paired: the same hidden compound, the
same people and the same noise. The card reports the mean paired gap with its standard error
and how often the reference wins. Z' between the two reward distributions (the statistic used
in drugdev-gym) is not used here: the hidden tasks differ so much from one another that the
spread of rewards is dominated by the task mix, and no policy could reach Z' 0.5.
"""
from __future__ import annotations

import numpy as np

from .env import make
from .interventions import GEROPROTECTIVE_THRESHOLD
from .policies import MISTAKES, POLICIES, make_policy, run_episode

ENROLMENT_GRID = (12, 20, 30, 60, 100, 150)


def paired(reference: np.ndarray, other: np.ndarray) -> dict:
    d = reference - other
    gap = float(d.mean())
    se = float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else float("nan")
    wins = float(np.mean(d > 0) + 0.5 * np.mean(d == 0))
    if gap >= 3 * se and gap > 0:
        verdict = "punished"
    elif gap <= -3 * se and gap < 0:
        verdict = "inverted"
    else:
        verdict = "blind"
    return {"gap": gap, "se": se, "win_rate": wins, "verdict": verdict}


def qc_card(n_seeds: int = 1000, first_seed: int = 0) -> dict:
    if n_seeds < 2:
        raise ValueError("n_seeds must be at least 2")
    seeds = range(first_seed, first_seed + n_seeds)
    res, by_iv, ref_cells = {}, {}, {}
    wrong = {"total": 0, "missed_real_effects": 0, "false_alarms": 0, "truth_within_0.3_years_of_threshold": 0}
    for name, policy in POLICIES.items():
        rewards, errors, calls, ivs = [], [], [], []
        for seed in seeds:
            reward, info = run_episode(make(seed=seed), policy)
            rewards.append(reward); errors.append(info["abs_error"]); calls.append(info["call_correct"])
            ivs.append(info["intervention"])
            if name == "reference":
                ref_cells.setdefault((info["intervention"], info["dose"]), []).append(info["call_correct"])
                if not info["call_correct"]:
                    wrong["total"] += 1
                    wrong["missed_real_effects" if info["geroprotective"] else "false_alarms"] += 1
                    wrong["truth_within_0.3_years_of_threshold"] += abs(info["true_effect_years"] - GEROPROTECTIVE_THRESHOLD) < 0.3
        res[name] = (np.array(rewards), np.array(errors), np.array(calls, float))
        cell = {}
        for iv, e in zip(ivs, errors):
            cell.setdefault(iv, []).append(e)
        by_iv[name] = {iv: float(np.mean(v)) for iv, v in sorted(cell.items())}
    reference = res["reference"][0]
    rows = []
    for name, (rewards, errors, calls) in res.items():
        row = {"policy": name, "mean": float(rewards.mean()), "median_abs_error_years": float(np.median(errors)),
               "call_accuracy": float(calls.mean()), "changes": MISTAKES.get(name, "")}
        if name != "reference":
            row.update(paired(reference, rewards))
        rows.append(row)
    curve = []
    for n in ENROLMENT_GRID:
        out = [run_episode(make(seed=seed), make_policy({"n_per_arm": n})) for seed in seeds]
        rewards = np.array([o[0] for o in out])
        curve.append({"n_per_arm": n, "mean": float(rewards.mean()),
                      "call_accuracy": float(np.mean([o[1]["call_correct"] for o in out])),
                      "median_abs_error_years": float(np.median([o[1]["abs_error"] for o in out])),
                      **paired(reference, rewards)})
    weak = [{"archetype": iv, "dose": dose, "episodes": len(v), "call_accuracy": float(np.mean(v))}
            for (iv, dose), v in sorted(ref_cells.items())]
    return {"env": "clock_trial", "n_seeds": n_seeds, "first_seed": first_seed, "rows": rows,
            "mean_abs_error_by_intervention": by_iv, "enrolment_curve": curve, "reference_calls_by_cell": weak,
            "reference_wrong_calls": {k: int(v) for k, v in wrong.items()}}


def card_markdown(card: dict) -> str:
    last = card["first_seed"] + card["n_seeds"] - 1
    out = [f"# Environment QC: {card['env']}", "",
           f"Seeds {card['first_seed']} to {last}; every policy sees the same hidden compound, people and noise.", "",
           "| policy | what it changes | mean reward | median error (yr) | right call | gap to reference (SE) "
           "| reference wins | verdict |", "|---|---|---|---|---|---|---|---|"]
    for r in card["rows"]:
        if r["policy"] == "reference":
            tail = "reference | | "
        else:
            tail = f"{r['gap']:+.3f} ({r['se']:.3f}) | {100 * r['win_rate']:.0f}% | {r['verdict']}"
        out.append(f"| {r['policy']} | {r['changes']} | {r['mean']:.3f} | {r['median_abs_error_years']:.2f} | "
                   f"{100 * r['call_accuracy']:.0f}% | {tail}")
    out += ["", "Verdicts: punished = the policy scores lower than the reference by at least 3 standard errors of "
            "the paired gap; inverted = higher by at least 3; blind = neither, the reward cannot tell them apart "
            "on these seeds. 'Reference wins' is the share of paired seeds, ties counted as half.", ""]
    m = card["mean_abs_error_by_intervention"]
    ivs = list(m["reference"])
    out += ["## Where each policy goes wrong: mean absolute error in years, by hidden archetype", "",
            "| policy | " + " | ".join(ivs) + " |", "|---|" + "---|" * len(ivs)]
    for policy, row in m.items():
        cells = []
        for iv in ivs:
            flag = "**" if policy != "reference" and round(row[iv], 2) - round(m["reference"][iv], 2) >= 0.3 else ""
            cells.append(f"{flag}{row[iv]:.2f}{flag}")
        out.append(f"| {policy} | " + " | ".join(cells) + " |")
    out += ["", "Bold = at least 0.3 years worse than the reference on that archetype.", ""]
    out += ["## Reward against enrolment (reference analysis, only the arm size changed)", "",
            "| people per arm | mean reward | right call | median error (yr) | gap to reference (SE) |",
            "|---|---|---|---|---|"]
    for r in card["enrolment_curve"]:
        out.append(f"| {r['n_per_arm']} | {r['mean']:.3f} | {100 * r['call_accuracy']:.0f}% | "
                   f"{r['median_abs_error_years']:.2f} | {r['gap']:+.3f} ({r['se']:.3f}) |")
    out += ["", "## Where the reference itself gets the call wrong (cells under 90 percent)", "",
            "| archetype | dose level | episodes | right call |", "|---|---|---|---|"]
    for r in card["reference_calls_by_cell"]:
        if r["call_accuracy"] < 0.9:
            out.append(f"| {r['archetype']} | {r['dose']} | {r['episodes']} | {100 * r['call_accuracy']:.0f}% |")
    w = card["reference_wrong_calls"]
    out += ["", f"Wrong calls by the reference: {w['total']} of {card['n_seeds']}. Missed real effects: "
            f"{w['missed_real_effects']}. False alarms: {w['false_alarms']}. True effect within 0.3 years of the "
            f"threshold: {w['truth_within_0.3_years_of_threshold']}.", ""]
    return "\n".join(out)
