"""What every clock says about every intervention, next to the truth. The table the README leads with."""
from __future__ import annotations

import numpy as np

from .clocks import CLOCK_NAMES
from .env import make
from .interventions import INTERVENTIONS
from .policies import EXPERT_DESIGN, clock_effect


def readout_table(cohort: str, dose: int = 2, n_seeds: int = 20, n_per_arm: int = 150) -> list[dict]:
    """Mean treated-minus-placebo change per clock at 26 weeks (unadjusted), over n_seeds trials."""
    rows = []
    for name in INTERVENTIONS:
        per = {c: [] for c in CLOCK_NAMES}
        for seed in range(n_seeds):
            env = make(seed=seed, intervention=name, cohort=cohort, dose=dose)
            env.reset()
            obs, *_ = env.step({**EXPERT_DESIGN, "n_per_arm": n_per_arm})
            for c in CLOCK_NAMES:
                per[c].append(clock_effect(obs["rows"], c, 26, adjust=False))
        rows.append({"intervention": name, "truth": INTERVENTIONS[name].true_effect(dose, cohort),
                     **{c: float(np.mean(v)) for c, v in per.items()}})
    return rows


def readout_markdown(dose: int = 2, n_seeds: int = 20) -> str:
    out = ["# Clock readouts vs truth", "",
           f"Years, treated minus placebo, 26 weeks, dose level {dose}, 150 per arm, mean of {n_seeds} simulated "
           "trials. Truth = change in mean organ age. Bold = the clock is off by 0.5 years or more.", ""]
    for cohort in ("fibrosis", "healthy"):
        out += [f"## Cohort: {cohort}", "", "| intervention | TRUTH | " + " | ".join(CLOCK_NAMES) + " |",
                "|---|---|" + "---|" * len(CLOCK_NAMES)]
        for r in readout_table(cohort, dose, n_seeds):
            cells = []
            for c in CLOCK_NAMES:
                flag = "**" if abs(r[c] - r["truth"]) >= 0.5 else ""
                cells.append(f"{flag}{r[c]:+.1f}{flag}")
            out.append(f"| {r['intervention']} | {r['truth']:+.1f} | " + " | ".join(cells) + " |")
        out.append("")
    return "\n".join(out)
