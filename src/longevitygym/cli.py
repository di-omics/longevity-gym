"""longevity-gym CLI: spec | clocks | readouts | qc | play."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="longevity-gym")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("spec")
    q = sub.add_parser("qc"); q.add_argument("--seeds", type=int, default=400); q.add_argument("--out", default="results")
    sub.add_parser("clocks")
    sub.add_parser("readouts")
    p = sub.add_parser("play"); p.add_argument("--seed", type=int, default=0); p.add_argument("--policy", default="expert")
    a = ap.parse_args(argv)
    if a.cmd == "spec":
        from .env import make
        print(json.dumps(make(seed=0).spec(), indent=2))
    elif a.cmd == "clocks":
        from .clocks import clock_table
        print("| clock | family | target | trained on | analog of | features | r | MAE (yr) |\n|---|---|---|---|---|---|---|---|")
        for r in clock_table():
            print(f"| {r['clock']} | {r['family']} | {r['target']} | {r['trained_on']} | {r['analog_of']} | "
                  f"{r['n_features']} | {r['r']:.3f} | {r['mae_years']:.2f} |")
    elif a.cmd == "readouts":
        from .readouts import readout_markdown
        print(readout_markdown())
    elif a.cmd == "qc":
        from .envqc import card_markdown, qc_card
        card = qc_card(a.seeds)
        out = Path(a.out); out.mkdir(exist_ok=True)
        (out / "qc_clock_trial.json").write_text(json.dumps(card, indent=1) + "\n")
        (out / "qc_clock_trial.md").write_text(card_markdown(card))
        print(card_markdown(card))
    elif a.cmd == "play":
        from .env import make
        from .policies import POLICIES, run_episode
        reward, info = run_episode(make(seed=a.seed), POLICIES[a.policy])
        info.pop("design")
        print(json.dumps({"reward": round(reward, 4), **info}, indent=2, default=str))


if __name__ == "__main__":
    main()
