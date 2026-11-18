"""longevity-gym CLI: spec | clocks | seedcheck | readouts | qc | shortcut | play."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _emit(text: str, out: str | None, filename: str) -> None:
    print(text)
    if out:
        folder = Path(out)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / filename).write_text(text if text.endswith("\n") else text + "\n")


def main(argv=None):
    from .policies import POLICIES
    ap = argparse.ArgumentParser(prog="longevity-gym")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("spec", help="the task as an agent sees it")
    for name, text in (("clocks", "accuracy and sensitivities of the eight simulated clocks"),
                       ("seedcheck", "the same sensitivities after refitting with other training seeds"),
                       ("readouts", "what each clock reads per archetype, next to the truth")):
        p = sub.add_parser(name, help=text)
        p.add_argument("--out", default=None, help="also write the table into this folder")
    p = sub.add_parser("shortcut", help="can a memorising policy beat the reference? (a few minutes)")
    p.add_argument("--out", default=None, help="also write the table (md and json) into this folder")
    q = sub.add_parser("qc", help="the environment QC card")
    q.add_argument("--seeds", type=int, default=2000)
    q.add_argument("--out", default=None, help="also write the card (md and json) into this folder")
    p = sub.add_parser("play", help="run one episode with a scripted policy")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--policy", default="reference", choices=sorted(POLICIES))
    a = ap.parse_args(argv)
    if a.cmd == "spec":
        from .env import make
        print(json.dumps(make(seed=0).spec(), indent=2))
    elif a.cmd == "clocks":
        from .clocks import clock_table_markdown
        _emit(clock_table_markdown(), a.out, "clocks.md")
    elif a.cmd == "seedcheck":
        from .clocks import seed_check_markdown
        _emit(seed_check_markdown(), a.out, "clock_seed_check.md")
    elif a.cmd == "readouts":
        from .readouts import readout_markdown
        _emit(readout_markdown(), a.out, "readouts.md")
    elif a.cmd == "qc":
        if a.seeds < 2:
            ap.error("--seeds must be at least 2")
        from .envqc import card_markdown, qc_card
        card = qc_card(a.seeds)
        _emit(card_markdown(card), a.out, "qc_clock_trial.md")
        if a.out:
            (Path(a.out) / "qc_clock_trial.json").write_text(json.dumps(card, indent=1) + "\n")
    elif a.cmd == "shortcut":
        from .shortcut import shortcut_markdown, shortcut_table
        rows = shortcut_table()
        _emit(shortcut_markdown(rows), a.out, "shortcut.md")
        if a.out:
            (Path(a.out) / "shortcut.json").write_text(json.dumps(rows, indent=1) + "\n")
    elif a.cmd == "play":
        from .env import make
        from .policies import run_episode
        reward, info = run_episode(make(seed=a.seed), POLICIES[a.policy])
        info = {k: v for k, v in info.items() if k != "design"}
        print(json.dumps({"reward": round(reward, 4), **info}, indent=2, default=str))


if __name__ == "__main__":
    main()
