"""What every simulated clock says about every archetype, next to the simulated truth."""
from __future__ import annotations

import numpy as np

from .clocks import CLOCK_NAMES
from .env import make
from .interventions import INTERVENTIONS
from .policies import REFERENCE_DESIGN, clock_effect


def readout_table(cohort: str, dose: int = 2, n_seeds: int = 20, n_per_arm: int = 150) -> list[dict]:
    """Mean treated-minus-placebo change per clock at 26 weeks over n_seeds trials, at nominal potency."""
    rows = []
    for name in INTERVENTIONS:
        per = {c: [] for c in CLOCK_NAMES}
        truth = None
        for seed in range(n_seeds):
            env = make(seed=seed, intervention=name, cohort=cohort, dose=dose, potency=(1.0, 1.0))
            env.reset()
            obs, *_ = env.step({**REFERENCE_DESIGN, "n_per_arm": n_per_arm})
            truth = env.truth()["true_effect_years"]
            for c in CLOCK_NAMES:
                per[c].append(clock_effect(obs["rows"], c, 26))
        rows.append({"intervention": name, "truth": truth, **{c: float(np.mean(v)) for c, v in per.items()}})
    return rows


def readout_markdown(dose: int = 2, n_seeds: int = 20) -> str:
    out = ["# Simulated clock readouts vs simulated truth", "",
           f"Years, treated minus placebo, 26 weeks, dose level {dose}, nominal potency, 150 per arm, mean of "
           f"{n_seeds} simulated trials. TRUTH = change in mean organ age. Bold = the printed value is 0.5 years "
           "or more away from the printed truth. Not evidence about any real clock, drug or trial.", ""]
    for cohort in ("fibrosis", "healthy"):
        out += [f"## Cohort: {cohort}", "", "| archetype | TRUTH | " + " | ".join(CLOCK_NAMES) + " |",
                "|---|---|" + "---|" * len(CLOCK_NAMES)]
        for r in readout_table(cohort, dose, n_seeds):
            cells = []
            for c in CLOCK_NAMES:
                flag = "**" if abs(round(r[c], 1) - round(r["truth"], 1)) >= 0.45 else ""
                cells.append(f"{flag}{r[c]:+.1f}{flag}")
            out.append(f"| {r['intervention']} | {r['truth']:+.1f} | " + " | ".join(cells) + " |")
        out.append("")
    return "\n".join(out)
