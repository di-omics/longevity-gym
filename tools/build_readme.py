"""Build README.md from docs/README.template.md and the files in results/.

Every number in the README prose is a token in the template that is filled from results/, so
the text cannot drift from the tables. Run after regenerating results:

    python tools/build_readme.py            # rewrite README.md
    python tools/build_readme.py --check    # exit 1 if README.md is out of date
"""
from __future__ import annotations

import json
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
PROTEOMIC = ["prot_sparse_chrono", "prot_dense_chrono", "prot_sparse_mortality", "prot_age_mortality",
             "prot_dense_chrono_b", "prot_organ_chrono"]
CHRONO = ["prot_sparse_chrono", "prot_dense_chrono", "prot_dense_chrono_b", "prot_organ_chrono"]
MORTALITY = ["prot_sparse_mortality", "prot_age_mortality"]
EPI = ["epi_chrono", "epi_mortality"]
CLOCK_COLS = {"r": "r", "mae": "MAE (yr)", "organ": "per year of organ aging", "inflam": "per SD inflammation",
              "fibrosis": "per unit fibrosis activity", "mix": "per SD cell mix"}
PHRASES = {
    "no_placebo": "having no placebo arm",
    "plates_by_arm": "running each arm's follow-up samples on its own plate",
    "ignore_plate": "leaving the plate out of the analysis",
    "short_trial_4wk": "stopping at 4 weeks",
    "small_n_12": "enrolling 12 per arm instead of 30",
    "proteomics_only": "using the six proteomic clocks only",
    "epigenetics_only": "using the two methylation clocks only",
    "one_clock": "using the whole-panel chronological proteomic clock alone",
    "cherry_pick_best_clock": "reporting the best-looking clock",
    "average_all_clocks": "averaging all eight clocks",
}


def tables(path: Path) -> list[list[dict]]:
    """Every markdown table in a file, as a list of row dicts keyed by header."""
    out, header, rows = [], None, []
    for line in path.read_text().splitlines() + [""]:
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header is None:
                header = cells
            elif not set("".join(cells)) <= set("-: "):
                rows.append(dict(zip(header, cells)))
        elif header is not None:
            out.append(rows)
            header, rows = None, []
    return out


def num(text: str) -> float:
    return float(text.replace("*", "").replace("%", ""))


def body(path: Path, demote: bool = True) -> str:
    """A results file without its H1, sub-headings pushed down one level."""
    lines = path.read_text().rstrip("\n").split("\n")
    lines = lines[1:] if lines and lines[0].startswith("# ") else lines
    text = "\n".join(lines).strip("\n")
    return re.sub(r"^## ", "### ", text, flags=re.M) if demote else text


def bullet(text: str) -> str:
    return textwrap.fill(text, width=96, initial_indent="- ", subsequent_indent="  ")


def build() -> str:
    card = json.loads((RES / "qc_clock_trial.json").read_text())
    qc = {r["policy"]: r for r in card["rows"]}
    errs = card["mean_abs_error_by_intervention"]
    enrol = {str(r["n_per_arm"]): r for r in card["enrolment_curve"]}
    clock = {r["clock"]: r for r in tables(RES / "clocks.md")[0]}
    seed = {r["clock"]: r for r in tables(RES / "clock_seed_check.md")[0]}
    read_fib, read_healthy = tables(RES / "readouts.md")
    read = {"fibrosis": {r["archetype"]: r for r in read_fib}, "healthy": {r["archetype"]: r for r in read_healthy}}
    short = json.loads((RES / "shortcut.json").read_text())
    blocks = [k for k in short[0] if k not in ("policy", "design")]
    short = {(r["policy"], r["design"]): r for r in short}

    cval = lambda name, col: num(clock[name][CLOCK_COLS[col]])
    rd = lambda arch, col: num(read["fibrosis"][arch][col])
    d = {
        "n_seeds": str(card["n_seeds"]),
        "slope_min": f"{min(cval(c, 'organ') for c in clock):.2f}",
        "slope_max": f"{max(cval(c, 'organ') for c in clock):.2f}",
        "infl_mort": f"{sum(cval(c, 'inflam') for c in MORTALITY) / 2:.1f}",
        "infl_chrono_max": f"{max(abs(cval(c, 'inflam')) for c in CHRONO):.2f}",
        "fib_min": f"{min(cval(c, 'fibrosis') for c in PROTEOMIC):.2f}",
        "fib_max": f"{max(cval(c, 'fibrosis') for c in PROTEOMIC):.2f}",
        "antifib_truth": f"{abs(rd('antifibrotic', 'TRUTH')):.1f}",
        "antifib_prot_lo": f"{min(abs(rd('antifibrotic', c)) for c in PROTEOMIC):.1f}",
        "antifib_prot_hi": f"{max(abs(rd('antifibrotic', c)) for c in PROTEOMIC):.1f}",
        "antifib_epi": " and ".join(f"{abs(rd('antifibrotic', c)):.1f}" for c in EPI) + " years younger",
        "inflam_mort": f"{sum(abs(rd('anti_inflammatory', c)) for c in MORTALITY) / 2:.1f}",
        "reprog_truth": f"{abs(rd('reprogramming_like', 'TRUTH')):.1f}",
        "reprog_epi_lo": f"{min(abs(rd('reprogramming_like', c)) for c in EPI):.1f}",
        "reprog_epi_hi": f"{max(abs(rd('reprogramming_like', c)) for c in EPI):.1f}",
        "mix_epi": f"{abs(rd('immune_mobilizer', 'epi_chrono')):.1f}",
    }
    # claims the fixed prose makes; fail loudly if new results no longer support them
    assert all(rd("antifibrotic", c) < rd("antifibrotic", "TRUTH") for c in PROTEOMIC)
    assert all(abs(num(v)) < 0.3 for k, v in read["healthy"]["antifibrotic"].items() if k != "archetype")
    assert all(abs(rd("anti_inflammatory", c)) < 0.3 for c in CHRONO)
    assert all(abs(rd("reprogramming_like", c) - rd("reprogramming_like", "TRUTH")) < 0.5 for c in PROTEOMIC)
    for arch in ("senolytic_like", "mtor_like", "restriction_like"):
        assert all(rd(arch, c) < 0 for c in PROTEOMIC + EPI), arch
    for name in ("cherry_pick_best_clock", "plates_by_arm", "no_placebo", "short_trial_4wk", "proteomics_only",
                 "epigenetics_only", "average_all_clocks", "always_no", "always_yes"):
        assert qc[name]["verdict"] == "punished", name
    assert enrol["150"]["mean"] < enrol["12"]["mean"] and enrol["150"]["call_accuracy"] > enrol["12"]["call_accuracy"]
    assert max(enrol.values(), key=lambda r: r["mean"])["n_per_arm"] in (20, 30)
    same = "same design as the reference"
    for b in blocks:
        assert abs(short[("memoriser", same)][b]["gap"]) < 3 * short[("memoriser", same)][b]["se"] + 0.01
        assert short[("classify_regress", same)][b]["gap"] > 0
        for design in ("no placebo arm", "stop at 4 weeks", "plates by arm"):
            assert short[("classify_regress", design)][b]["gap"] < 0, design

    named = [p for p in PHRASES if p in qc]
    mild = [p for p in named if qc[p]["verdict"] == "punished" and qc[p]["gap"] < 0.04]
    blind = [p for p in named if qc[p]["verdict"] == "blind"]
    inverted = [p for p in named if qc[p]["verdict"] == "inverted"]
    listing = lambda ps: "; ".join(f"{PHRASES[p]} (gap {qc[p]['gap']:+.3f}, SE {qc[p]['se']:.3f})" for p in ps)
    d["mild_bullet"] = bullet("Punished, but only mildly: " + listing(mild) + ".") if mild else ""
    text = ""
    if blind:
        text = "**Blind spots, reported and not hidden.** The reward cannot tell the reference from " + listing(blind) + "."
        if "one_clock" in blind:
            text += (" In this simulator that clock is the one least sensitive to everything that is not aging, so"
                     " using it alone costs nothing. A harder version needs a mechanism that fools it.")
    if inverted:
        text += (" " if text else "") + "**Inverted:** the reward prefers " + listing(inverted) + " to the reference."
    d["blind_bullet"] = bullet(text or "**No blind spots on these seeds.** Every named mistake scores lower than "
                               "the reference by at least three standard errors.")
    weak = [c for c in card["reference_calls_by_cell"] if c["call_accuracy"] < 0.7]
    if [(c["archetype"], c["dose"]) for c in weak] == [("mtor_like", 3)]:
        c = weak[0]
        d["weak_cells_bullet"] = bullet(
            f"The reference has one weak cell: the mTOR-like archetype at dose level 3, where it makes the right "
            f"call {100 * c['call_accuracy']:.0f} percent of the time ({c['episodes']} episodes). A cell-mix shift "
            "pushes the chronological methylation clock the other way there, the methylation median shrinks "
            "toward zero, and the conservative rule reports too little. The covariates would reveal the shift, "
            "and the reference does not use them.")
        w = card["reference_wrong_calls"]
        assert w["missed_real_effects"] > 0.85 * w["total"]
        d["weak_cells_bullet"] += "\n" + bullet(
            f"The reference errs on the side of missing real effects: {w['missed_real_effects']} of its "
            f"{w['total']} wrong calls are real effects called not geroprotective, and in "
            f"{w['truth_within_0.3_years_of_threshold']} of the {w['total']} the true effect is within 0.3 years of "
            "the half-year threshold. The clocks under-read real change by about a fifth and the rule is "
            "conservative on top of that.")
    else:
        cells = "; ".join(f"{c['archetype']} at dose level {c['dose']} ({100 * c['call_accuracy']:.0f} percent)" for c in weak)
        d["weak_cells_bullet"] = bullet("Cells where the reference makes the right call under 70 percent of the "
                                        "time: " + (cells or "none") + ".")

    def token(m):
        kind, *args = m.group(1).split(":")
        if kind == "TABLE":
            if args[0] == "clocks":
                return (RES / "clocks.md").read_text().strip("\n")
            if args[0] == "readouts":
                text = body(RES / "readouts.md", demote=False)
                caption, rest = text.split("## Cohort: fibrosis")
                table = rest.split("## Cohort: healthy")[0].strip("\n")
                return (textwrap.fill(" ".join(caption.split()) + " Fibrosis cohort shown; the healthy cohort is in "
                                      "[results/readouts.md](results/readouts.md).", width=96) + "\n\n" + table)
            if args[0] == "qc":
                return body(RES / "qc_clock_trial.md")
            if args[0] == "shortcut":
                return body(RES / "shortcut.md")
        if kind == "d":
            return d[args[0]]
        if kind == "qc":
            row, field = qc[args[0]], args[1]
            return {"mean": f"{row['mean']:.2f}", "err": f"{row['median_abs_error_years']:.2f}",
                    "call": f"{100 * row['call_accuracy']:.0f}", "gap": f"{abs(row.get('gap', 0)):.2f}"}[field]
        if kind == "err":
            return f"{errs[args[0]][args[1]]:.2f}"
        if kind == "enrol":
            row = enrol[args[0]]
            return {"mean": f"{row['mean']:.2f}", "call": f"{100 * row['call_accuracy']:.0f}"}[args[1]]
        if kind == "clock":
            return clock[args[0]][CLOCK_COLS[args[1]]]
        if kind == "seed":
            return seed[args[0]][CLOCK_COLS[args[1]]].replace("+", "")
        if kind == "short":
            cell = short[(args[0], args[1])][blocks[int(args[2])]]
            return f"{cell['mean']:.3f}" if args[3] == "mean" else f"{cell['gap']:+.3f}".lstrip("+")
        raise KeyError(m.group(1))

    text = re.sub(r"<<([^<>]+)>>", token, (ROOT / "docs" / "README.template.md").read_text())
    text = re.sub(r"\n{3,}", "\n\n", text)
    assert "<<" not in text and ">>" not in text
    text.encode("ascii")
    return text


if __name__ == "__main__":
    new = build()
    target = ROOT / "README.md"
    if "--check" in sys.argv:
        if target.read_text() != new:
            sys.exit("README.md is out of date: run python tools/build_readme.py")
        print("README.md matches results/")
    else:
        target.write_text(new)
        print(f"wrote {target} ({len(new.splitlines())} lines)")
