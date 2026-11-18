"""Build README.md from docs/README.template.md and the files in results/.

Every result number in the README prose is a token in the template that is filled from
results/, and the sentences whose wording depends on a result (which mistakes are punished,
what the shortcut check shows) are generated here, so the text cannot drift from the tables.
Design constants (pool size, number of archetypes, seed counts) are written by hand in the
template. Run after regenerating results:

    python tools/build_readme.py            # rewrite README.md
    python tools/build_readme.py --check    # exit 1 if README.md is out of date
"""
from __future__ import annotations

import json
import math
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
CHRONO = ["prot_sparse_chrono", "prot_dense_chrono", "prot_dense_chrono_b", "prot_organ_chrono"]
MORTALITY = ["prot_sparse_mortality", "prot_age_mortality"]
PROTEOMIC = CHRONO + MORTALITY
EPI = ["epi_chrono", "epi_mortality"]
CLOCK_COLS = {"r": "r", "mae": "MAE (yr)", "organ": "per year of organ aging", "inflam": "per SD inflammation",
              "fibrosis": "per unit fibrosis activity", "mix": "per SD cell mix"}
PHRASES = {
    "no_placebo": "having no placebo arm",
    "plates_by_arm": "running each arm's follow-up samples on its own plate",
    "ignore_plate": "leaving the plate out of the analysis",
    "short_trial_4wk": "stopping at 4 weeks",
    "small_n_12": "enrolling 12 per arm instead of 30",
    "no_covariates": "not measuring the two covariates",
    "raw_clock_changes": "ignoring the calibration cards",
    "proteomics_only": "using the six proteomic clocks only",
    "epigenetics_only": "using the two methylation clocks only",
    "one_clock": "using the whole-panel chronological proteomic clock alone",
    "cherry_pick_best_clock": "reporting the best-looking clock",
    "average_all_clocks": "averaging all eight clocks",
}
OWN_BULLET = ("proteomics_only", "epigenetics_only", "average_all_clocks", "one_clock")
SAME = "same design as the reference"


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


def judged(gap: float, se: float, win: str, lose: str, tie: str) -> str:
    return win if gap >= 3 * se else lose if gap <= -3 * se else tie


def build() -> str:
    card = json.loads((RES / "qc_clock_trial.json").read_text())
    qc = {r["policy"]: r for r in card["rows"]}
    errs = card["mean_abs_error_by_intervention"]
    enrol = {str(r["n_per_arm"]): r for r in card["enrolment_curve"]}
    clock = {r["clock"]: r for r in tables(RES / "clocks.md")[0]}
    seed = {r["clock"]: r for r in tables(RES / "clock_seed_check.md")[0]}
    read_fib, read_healthy = tables(RES / "readouts.md")
    read = {"fibrosis": {r["archetype"]: r for r in read_fib}, "healthy": {r["archetype"]: r for r in read_healthy}}
    short_rows = json.loads((RES / "shortcut.json").read_text())
    blocks = [k for k in short_rows[0] if k not in ("policy", "design")]
    short = {(r["policy"], r["design"]): r for r in short_rows}
    assert len(blocks) == 3 and "potency" in blocks[2]

    cval = lambda name, col: num(clock[name][CLOCK_COLS[col]])
    rd = lambda arch, col: num(read["fibrosis"][arch][col])
    d = {
        "n_seeds": str(card["n_seeds"]),
        "last_seed": str(card["first_seed"] + card["n_seeds"] - 1),
        "zero_share": f"{100 * card['task_mix']['true_effect_exactly_zero']:.0f}",
        "enrol_peak": str(max(enrol.values(), key=lambda r: r["mean"])["n_per_arm"]),
        "slope_min": f"{min(cval(c, 'organ') for c in clock):.2f}",
        "slope_max": f"{max(cval(c, 'organ') for c in clock):.2f}",
        "infl_mort": f"{sum(cval(c, 'inflam') for c in MORTALITY) / 2:.1f}",
        "infl_other_max": f"{max(abs(cval(c, 'inflam')) for c in CHRONO + EPI):.2f}",
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
    # What the fixed prose claims. Fail loudly if new results no longer support it.
    assert all(rd("antifibrotic", c) < rd("antifibrotic", "TRUTH") < 0 for c in PROTEOMIC)
    assert all(rd("antifibrotic", c) <= 0 for c in EPI)
    assert all(abs(num(v)) < 0.3 for k, v in read["healthy"]["antifibrotic"].items() if k != "archetype")
    assert all(rd("anti_inflammatory", c) < -0.5 for c in MORTALITY)
    assert all(abs(rd("anti_inflammatory", c)) < 0.3 for c in CHRONO + EPI)
    assert all(abs(rd("reprogramming_like", c) - rd("reprogramming_like", "TRUTH")) < 0.5 for c in PROTEOMIC)
    assert all(abs(rd("immune_mobilizer", c)) < 0.3 for c in PROTEOMIC) and rd("immune_mobilizer", "epi_chrono") < -0.5
    for arch in ("senolytic_like", "mtor_like", "restriction_like"):
        assert all(rd(arch, c) < 0 for c in PROTEOMIC + EPI), arch
    assert all(cval(c, "fibrosis") > 0.2 for c in PROTEOMIC) and all(abs(cval(c, "fibrosis")) < 0.05 for c in EPI)
    assert max(cval(c, "fibrosis") for c in ("prot_dense_chrono", "prot_dense_chrono_b")) < min(
        cval(c, "fibrosis") for c in PROTEOMIC if "dense" not in c)
    for name in ("proteomics_only", "epigenetics_only", "average_all_clocks", "always_no", "always_yes"):
        assert qc[name]["verdict"] == "punished", name
    assert errs["proteomics_only"]["antifibrotic"] > errs["reference"]["antifibrotic"] + 0.2
    assert enrol["150"]["mean"] < enrol["12"]["mean"] and enrol["150"]["call_accuracy"] > enrol["12"]["call_accuracy"]

    listing = lambda ps: "; ".join(f"{PHRASES[p]} (gap {qc[p]['gap']:+.3f}, SE {qc[p]['se']:.3f})" for p in ps)
    named = [p for p in PHRASES if p in qc]
    top = sorted([p for p in named if p not in OWN_BULLET], key=lambda p: -qc[p]["gap"])[:4]
    assert all(qc[p]["verdict"] == "punished" for p in top)
    parts = [f"{PHRASES[p]} ({qc[p]['gap']:.2f}" + (" reward lost)" if i == 0 else ")") for i, p in enumerate(top)]
    d["costliest_bullet"] = bullet("The costliest choices are " + ", ".join(parts[:-1]) + " and " + parts[-1] + ".")

    oc, e1, e2 = qc["one_clock"], errs["one_clock"]["antifibrotic"], errs["reference"]["antifibrotic"]
    if oc["verdict"] == "punished":
        d["one_clock_bullet"] = bullet(
            f"**One clock is not enough either.** Using the whole-panel chronological proteomic clock alone, with "
            f"its calibration card, loses {oc['gap']:.2f} (SE {oc['se']:.3f}). It is the proteomic clock that reads "
            f"fibrosis least, and it is still fooled on the antifibrotic archetype: its error there is {e1:.2f} years "
            f"against {e2:.2f} for the reference.")
    else:
        word = "scores higher than the reference" if oc["verdict"] == "inverted" else "cannot be told from the reference"
        d["one_clock_bullet"] = bullet(
            f"**The reward does not yet pay for checking one modality against the other.** Using the whole-panel "
            f"chronological proteomic clock alone, with its calibration card, {word} (gap {oc['gap']:+.3f}, SE "
            f"{oc['se']:.3f}), although its error on the antifibrotic archetype is {e1:.2f} years against {e2:.2f}. "
            "A harder version needs a mechanism that fools that clock more often.")
    rest = [p for p in named if p not in OWN_BULLET and p not in top]
    mild = [p for p in rest if qc[p]["verdict"] == "punished"]
    blind = [p for p in rest if qc[p]["verdict"] == "blind"]
    inverted = [p for p in rest if qc[p]["verdict"] == "inverted"]
    d["mild_bullet"] = bullet("Also punished, by less: " + listing(mild) + ".") if mild else ""
    text = ""
    if blind:
        text = "**Blind spots, reported and not hidden.** The reward cannot tell the reference from " + listing(blind) + "."
    if inverted:
        text += (" " if text else "") + "**Inverted:** the reward prefers " + listing(inverted) + " to the reference."
    d["blind_bullet"] = bullet(text) if text else ""

    weak = [c for c in card["reference_calls_by_cell"] if c["call_accuracy"] < 0.7]
    if weak:
        cells = "; ".join(f"{c['archetype']} at dose level {c['dose']} ({100 * c['call_accuracy']:.0f} percent of "
                          f"{c['episodes']} episodes)" for c in weak)
        d["weak_cells_bullet"] = bullet("On these seeds the reference makes the right call under 70 percent of the "
                                        "time in: " + cells + ". With so few episodes per cell the figures are "
                                        "rough. The table above lists every cell under 90 percent.")
    else:
        d["weak_cells_bullet"] = bullet("No cell of the reference is under 70 percent right calls on these seeds. "
                                        "The table above lists the cells under 90 percent.")
    w = card["reference_wrong_calls"]
    d["wrong_calls_bullet"] = bullet(
        f"Of the reference's {w['total']} wrong calls, {w['missed_real_effects']} are real effects called not "
        f"geroprotective and {w['false_alarms']} are false alarms. In {w['truth_within_0.3_years_of_threshold']} of "
        f"the {w['total']} the true effect is within 0.3 years of the half-year threshold.")

    def pooled(policy, design):
        a, b = short[(policy, design)][blocks[0]], short[(policy, design)][blocks[1]]
        return (a["gap"] + b["gap"]) / 2, math.sqrt(a["se"] ** 2 + b["se"] ** 2) / 2

    ref_row = short[("reference", "reference design")]
    means = lambda policy, design: [short[(policy, design)][b]["mean"] for b in blocks]
    mg, ms = pooled("memoriser", SAME)
    m = means("memoriser", SAME)
    r = [ref_row[b]["mean"] for b in blocks]
    d["memoriser_bullet"] = bullet(
        f"**Pure memorising.** Recognising the archetype and answering with a memorised effect scores {m[0]:.3f} and "
        f"{m[1]:.3f} on two blocks of new seeds, against {r[0]:.3f} and {r[1]:.3f} for the reference. Pooled over the "
        f"two blocks the difference is {mg:+.3f} (SE {ms:.3f}): "
        + judged(mg, ms, "memorising beats the reference, so this reward still pays for it.",
                 "memorising loses.", "a tie within the noise, so memorising neither wins nor clearly loses."))
    lg, ls = pooled("classify_regress", SAME)
    c = means("classify_regress", SAME)
    d["learner_bullet"] = bullet(
        f"**Learning inside the task mix.** Recognising the archetype and then estimating inside it scores "
        f"{c[0]:.3f} and {c[1]:.3f}. Pooled difference to the reference: {lg:+.3f} (SE {ls:.3f}): "
        + judged(lg, ls, "it beats the reference.", "it loses to the reference.", "a tie within the noise."))
    om, ol = short[("memoriser", SAME)][blocks[2]], short[("classify_regress", SAME)][blocks[2]]
    word = lambda c: judged(c["gap"], c["se"], "stays ahead of the reference", "falls behind the reference",
                            "stays level with the reference")
    d["off_range_bullet"] = bullet(
        f"**Outside the potency range they were trained on** (aging potency forced to 2.5) the memoriser scores "
        f"{om['mean']:.3f} and the learner {ol['mean']:.3f}, against {r[2]:.3f} for the reference (differences "
        f"{om['gap']:+.3f}, SE {om['se']:.3f}, and {ol['gap']:+.3f}, SE {ol['se']:.3f}). The memoriser {word(om)}; "
        f"the learner {word(ol)}. A policy that reads the clocks should not care about the range, so this column "
        "is the one to watch when a stronger learner is trained here.")
    full = means("classify_regress", SAME)
    cost = {k: [full[i] - means("classify_regress", k)[i] for i in (0, 1)]
            for k in ("no placebo arm", "stop at 4 weeks", "plates by arm", "12 per arm")}
    assert all(v > 0 for k in ("no placebo arm", "stop at 4 weeks", "plates by arm") for v in cost[k])
    d["lessons_bullet"] = bullet(
        f"**The design lessons still cost the learner.** Against its own full design, taking away the placebo arm "
        f"costs it {cost['no placebo arm'][0]:.3f}, stopping at 4 weeks {cost['stop at 4 weeks'][0]:.3f} and putting "
        f"each arm on its own plate {cost['plates by arm'][0]:.3f} on the first block "
        f"({cost['no placebo arm'][1]:.3f}, {cost['stop at 4 weeks'][1]:.3f} and {cost['plates by arm'][1]:.3f} on "
        f"the second). Enrolling 12 per arm instead of 30 changes its score by {-cost['12 per arm'][0]:+.3f} and "
        f"{-cost['12 per arm'][1]:+.3f}.")

    # ---- the real-data section
    real = json.loads((RES / "real_check.json").read_text())
    cal = json.loads((RES / "qc_clock_trial_calibrated.json").read_text())
    assert cal["noise"] == "calibrated" and cal["n_seeds"] == card["n_seeds"]
    calqc = {r["policy"]: r for r in cal["rows"]}
    calenrol = {str(r["n_per_arm"]): r for r in cal["enrolment_curve"]}
    est = [v["estimate"] for v in real["real"]["change_sd"].values()]
    quiet = real["default_too_quiet_by"]
    assert quiet["min"] > 2
    d["real_quiet_bullet"] = bullet(
        f"**The simulator is far too quiet.** For the six real clocks in that trial's patients, one person's change "
        f"between two visits has an SD of about {min(est):.1f} to {max(est):.1f} years. That covers everything that "
        f"makes two visits differ: assay noise, short-term biology and, in the treated arms, differences in "
        f"response. The estimate is indirect: it is backed out of the paper's published test statistics. The "
        f"simulator's default is {quiet['min']:.1f} to {quiet['max']:.1f} times smaller.")
    analog = real["analog"]
    chrono = [n for n in analog if "mortality" not in n]
    mort = [n for n in analog if "mortality" in n]
    def span(source, rows_, cols_, real_names):
        vals = [source[analog[a] if real_names else a][analog[b] if real_names else b]
                for a in rows_ for b in cols_ if a != b]
        return f"{min(vals):.2f} to {max(vals):.2f}"
    rc, dc, cc = real["real"]["corr"], real["default"]["corr"], real["calibrated"]["corr"]
    d["real_corr_bullet"] = bullet(
        f"**Simulated clocks agree with each other far more than real ones.** Over samples, the four real "
        f"chronological clocks correlate {span(rc, chrono, chrono, True)} with each other and "
        f"{span(rc, chrono, mort, True)} with the two mortality clocks. In the simulator those correlations are "
        f"{span(dc, chrono, chrono, False)} and {span(dc, chrono, mort, False)}, and calibrating the noise only "
        f"brings them to {span(cc, chrono, chrono, False)} and {span(cc, chrono, mort, False)}. Real patients differ "
        "along more dimensions than these simulated ones, and no noise setting fixes that.")
    cr, dr = calqc["reference"], qc["reference"]
    peak = max(calenrol.values(), key=lambda r: r["mean"])["n_per_arm"]
    d["real_card_bullet"] = bullet(
        f"**With real-world noise the task is much harder.** `make(seed, noise=\"calibrated\")` adds reading noise to "
        f"every clock until its change-score SD matches the real estimate. Under it the reference analysis scores "
        f"{cr['mean']:.2f} instead of {dr['mean']:.2f} and makes the right call {100 * cr['call_accuracy']:.0f} "
        f"percent of the time instead of {100 * dr['call_accuracy']:.0f}, at 30 per arm. At 150 per arm it makes the "
        f"right call {100 * calenrol['150']['call_accuracy']:.0f} percent of the time, and on the enrolment grid the "
        f"reward is highest at {peak} per arm. The full card is in "
        "[results/qc_clock_trial_calibrated.md](results/qc_clock_trial_calibrated.md).")
    still = [p for p in named if calqc[p]["verdict"] == "punished"]
    lost = [p for p in named if calqc[p]["verdict"] != "punished"]
    text = f"Under calibrated noise {len(still)} of the {len(named)} named mistakes are still punished."
    if lost:
        text += (" The reward can no longer tell the reference from: "
                 + "; ".join(f"{PHRASES[p]} (gap {calqc[p]['gap']:+.3f}, SE {calqc[p]['se']:.3f}"
                             + (", the mistake scores higher" if calqc[p]["verdict"] == "inverted" else "") + ")"
                             for p in lost) + ".")
    d["real_card_verdicts_bullet"] = bullet(text)
    sens = {r["shared_fraction"]: r for r in real["shared_fraction_sensitivity"]}
    d["real_share_bullet"] = bullet(
        f"Two things in the calibrated profile are assumptions, not measurements. First, half of the added noise "
        f"is shared by the clocks of one modality in a sample. That choice matters: using one clock alone loses "
        f"{sens[0.0]['one_clock']['gap']:.2f} if none of the noise is shared, {sens[0.5]['one_clock']['gap']:.2f} at "
        f"one half and {sens[1.0]['one_clock']['gap']:.2f} if all of it is (600 seeds, SE about "
        f"{sens[0.5]['one_clock']['se']:.2f}). Second, the two methylation clocks, for which [1] has no data, get "
        "the mean target of the four chronological proteomic clocks.")

    def token(m):
        kind, *args = m.group(1).split(":")
        if kind == "TABLE":
            if args[0] == "clocks":
                return "\n".join(l for l in (RES / "clocks.md").read_text().splitlines() if l.startswith("|"))
            if args[0] == "readouts":
                text = body(RES / "readouts.md", demote=False)
                caption, rest_ = text.split("## Cohort: fibrosis")
                table = rest_.split("## Cohort: healthy")[0].strip("\n")
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
            if field == "gap":
                assert row["gap"] > 0, args[0]          # the prose around this token says "loses"
                return f"{row['gap']:.2f}"
            return {"mean": f"{row['mean']:.2f}", "err": f"{row['median_abs_error_years']:.2f}",
                    "call": f"{100 * row['call_accuracy']:.0f}"}[field]
        if kind == "err":
            return f"{errs[args[0]][args[1]]:.2f}"
        if kind == "enrol":
            row = enrol[args[0]]
            return {"mean": f"{row['mean']:.2f}", "call": f"{100 * row['call_accuracy']:.0f}"}[args[1]]
        if kind == "clock":
            return clock[args[0]][CLOCK_COLS[args[1]]]
        if kind == "seed":
            return seed[args[0]][CLOCK_COLS[args[1]]].replace("+", "")
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
