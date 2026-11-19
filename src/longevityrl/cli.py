"""Run Longevity RL simulation benchmarks and reports."""
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


def _replay(args) -> None:
    from .replay import compare_campaigns, run_replay
    settings = dict(seed=args.seed, rounds=args.rounds, batch_size=args.batch_size,
                    warm_start=args.warm_start)
    if args.campaigns == 1:
        report = run_replay(**settings)
    else:
        report = compare_campaigns(**settings, campaigns=args.campaigns)
    if args.json:
        print(json.dumps(report, allow_nan=False))
    elif args.campaigns == 1:
        print(f"Synthetic joint hits | seed {args.seed} | {args.batch_size} new candidates per round")
        print("policy\t" + "\t".join(f"round {i}" for i in range(1, args.rounds + 1)))
        for policy, rounds in report["policies"].items():
            print(policy + "\t" + "\t".join(str(row["cumulative_hits"]) for row in rounds))
    else:
        print(f"{args.campaigns} paired synthetic campaigns | {args.rounds * args.batch_size} "
              "new candidates per policy per campaign")
        print("policy\tmean joint hits")
        for policy, hits in report["mean_hits"].items():
            print(f"{policy}\t{hits:.2f}")
        for policy, delta in report["planner_comparisons"].items():
            print(f"planner vs {policy}: {delta['wins']} wins, {delta['ties']} ties, "
                  f"{delta['losses']} losses")


def main(argv=None):
    from .policies import POLICIES
    ap = argparse.ArgumentParser(prog="longevity-rl", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("spec", help="the task as an agent sees it")
    b = sub.add_parser("benchmark", help="compare estimates of aging effects on held-out simulated trials")
    b.add_argument("--seed", type=int, default=0, help="first training seed")
    b.add_argument("--train-seeds", type=int, default=32)
    b.add_argument("--test-seeds", type=int, default=16)
    b.add_argument("--noise", choices=["default", "calibrated"], default="default")
    b.add_argument("--json", action="store_true", help="include each simulated trial and model estimate")
    r = sub.add_parser("replay", help="compare few-shot batch policies with equal synthetic assay budgets")
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--campaigns", type=int, default=1)
    r.add_argument("--rounds", type=int, default=4)
    r.add_argument("--batch-size", type=int, default=24)
    r.add_argument("--warm-start", type=int, default=8, help="starting labels shared by all policies")
    r.add_argument("--json", action="store_true", help="print the selection trace or multi-campaign summary")
    for name, text in (("clocks", "accuracy and sensitivities of the eight simulated clocks"),
                       ("seedcheck", "the same sensitivities after refitting with other training seeds"),
                       ("readouts", "what each clock reads per archetype, next to the truth")):
        p = sub.add_parser(name, help=text)
        p.add_argument("--out", default=None, help="also write the table into this folder")
    p = sub.add_parser("shortcut", help="can a memorising policy beat the reference? (a few minutes)")
    p.add_argument("--out", default=None, help="also write the table (md and json) into this folder")
    q = sub.add_parser("qc", help="the environment QC card")
    q.add_argument("--seeds", type=int, default=2000)
    q.add_argument("--noise", default="default", choices=["default", "calibrated"],
                   help="clock noise: the simulator's own, or calibrated to real clock readouts")
    q.add_argument("--out", default=None, help="also write the card (md and json) into this folder")
    p = sub.add_parser("realcheck", help="the simulator's clock noise against real clock readouts")
    p.add_argument("--out", default=None, help="also write the report (md and json) into this folder")
    p = sub.add_parser("play", help="run one episode with a scripted policy")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--policy", default="reference", choices=sorted(POLICIES))
    a = ap.parse_args(argv)
    if a.cmd == "replay":
        try:
            _replay(a)
        except ValueError as exc:
            ap.error(str(exc))
    elif a.cmd == "spec":
        from .env import make
        print(json.dumps(make(seed=0).spec(), indent=2))
    elif a.cmd == "benchmark":
        from .benchmark import run_benchmark
        try:
            report = run_benchmark(train_seeds=a.train_seeds, test_seeds=a.test_seeds,
                                   seed=a.seed, noise=a.noise)
        except ValueError as exc:
            ap.error(str(exc))
        if a.json:
            print(json.dumps(report, allow_nan=False))
        else:
            print(f"Longevity RL | {a.test_seeds} held-out simulated trials | {a.noise} noise")
            print("policy\tmean reward\tcall accuracy\tmean absolute error (years)")
            for name, row in report["policies"].items():
                print(f"{name}\t{row['mean_reward']:.3f}\t{row['call_accuracy']:.1%}\t"
                      f"{row['mean_abs_error_years']:.3f}")
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
        card = qc_card(a.seeds, noise=a.noise)
        stem = "qc_clock_trial" + ("" if a.noise == "default" else "_" + a.noise)
        _emit(card_markdown(card), a.out, stem + ".md")
        if a.out:
            (Path(a.out) / (stem + ".json")).write_text(json.dumps(card, indent=1) + "\n")
    elif a.cmd == "realcheck":
        from .realcheck import real_check, real_check_markdown
        res = real_check()
        _emit(real_check_markdown(res), a.out, "real_check.md")
        if a.out:
            (Path(a.out) / "real_check.json").write_text(json.dumps(res, indent=1) + "\n")
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
