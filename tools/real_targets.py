"""Recompute the real-data aggregates used by longevityrl/realcheck.py.

Input: the supplementary tables workbook of reference [1] in the README (an open access article, CC BY 4.0),
file 41587_2026_3286_MOESM3_ESM.xlsx from the article's "Supplementary information" section.
It is not stored in this repo. Download it yourself and run:

    python tools/real_targets.py /path/to/41587_2026_3286_MOESM3_ESM.xlsx

Only aggregates leave this script: six noise estimates, a 6 x 6 correlation matrix and six
standard deviations. The workbook's prediction table (S2) lists 168 samples with no participant,
arm or visit label. Nothing here tries to link samples back to participants.

How the noise of a change score is estimated. Table S4 gives, for every clock, week and treated
arm, the Mann-Whitney U statistic of the change from baseline (treated against placebo) and both
group means. Under a normal model with one common SD, U / (n1 * n2) estimates
Phi((mean_treated - mean_placebo) / (SD * sqrt(2))). The SD is fitted by least squares over the
nine comparisons of a clock. A parametric bootstrap gives the 5th, 50th and 95th percentile.
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from statistics import NormalDist

import numpy as np

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/package/2006/relationships"}
# column of table S2 for each of the six clocks of the paper's main analysis
S2_COLUMNS = {"ProtAge": "Austin_2024(original)", "OrganAge_chrono": "Goeminne_2025(chrono_conventional_none)",
              "ipfP3GPT": "Galkin_2025(v6_standard)", "PAOPAC": "Han_2025(Conventional)",
              "OrganAge_mortality": "Goeminne_2025(mortality_conventional_none)", "PAC": "Kuo_2024(none)"}
ORDER = list(S2_COLUMNS)


def workbook(path):
    """A minimal read-only XLSX reader (standard library only): {sheet name: rows of cell values}."""
    z = zipfile.ZipFile(path)
    shared = ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"]))
              for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
    rels = {r.get("Id"): r.get("Target")
            for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).findall("p:Relationship", NS)}
    out = {}
    for sh in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", NS):
        target = rels[sh.get("{%s}id" % NS["r"])]
        target = target.lstrip("/") if target.startswith("/") else "xl/" + target
        rows = []
        for row in ET.fromstring(z.read(target)).iter("{%s}row" % NS["m"]):
            cells = {}
            for c in row.findall("m:c", NS):
                v, t = c.find("m:v", NS), c.get("t")
                if v is None:
                    continue
                col = 0
                for ch in re.match(r"[A-Z]+", c.get("r")).group(0):
                    col = col * 26 + ord(ch) - 64
                if t == "s":
                    cells[col - 1] = shared[int(v.text)]
                else:
                    try:
                        cells[col - 1] = float(v.text)
                    except ValueError:
                        cells[col - 1] = v.text
            rows.append([cells.get(i) for i in range(max(cells) + 1)] if cells else [])
        out[sh.get("name")] = rows
    return out


def fit_sd(comparisons) -> float:
    """comparisons: (U, n_treated, n_placebo, mean_treated, mean_placebo) tuples of one clock."""
    grid = np.arange(0.3, 12.0, 0.01)
    cdf = NormalDist().cdf
    loss = [sum((u / (n1 * n2) - cdf((mt - mp) / (s * 2 ** 0.5))) ** 2 for u, n1, n2, mt, mp in comparisons) for s in grid]
    return float(grid[int(np.argmin(loss))])


def main(path: str) -> dict:
    wb = workbook(path)
    header = wb["S4"][1]
    rows = [dict(zip(header, r)) for r in wb["S4"][2:] if r and len(r) > 2 and r[1]]
    rng = np.random.default_rng(1)
    change_sd = {}
    for clock in ORDER:
        rs = [r for r in rows if r["Article name"] == clock]
        assert len(rs) == 9, (clock, len(rs))
        comps = [(r["U_statistic"], r["n_treatment"], r["n_placebo"], r["treatment_mean"], r["placebo_mean"]) for r in rs]
        est = fit_sd(comps)
        boot = []
        for _ in range(500):
            placebo, fake = {}, []
            for r in rs:
                n1, n2, week = int(r["n_treatment"]), int(r["n_placebo"]), r["Time_Point"]
                if week not in placebo:                       # one placebo sample per week, shared by the three arms
                    placebo[week] = rng.normal(r["placebo_mean"], est, n2)
                t = rng.normal(r["treatment_mean"], est, n1)
                fake.append((float(np.sum(t[:, None] > placebo[week][None, :])), n1, n2, float(t.mean()), float(placebo[week].mean())))
            boot.append(fit_sd(fake))
        lo, mid, hi = (float(v) for v in np.percentile(boot, [5, 50, 95]))
        change_sd[clock] = {"estimate": round(est, 2), "boot_p05": round(lo, 2), "boot_p50": round(mid, 2), "boot_p95": round(hi, 2)}
    header = wb["S2"][3]
    data = np.array([[float(v) for v in r[1:]] for r in wb["S2"][4:]])
    assert data.shape[0] == 168
    cols = np.array([data[:, header.index(S2_COLUMNS[c]) - 1] for c in ORDER])
    corr = np.corrcoef(cols)
    # published numbers that must come out of this file if it was read correctly
    eff = {(r["Article name"], r["Treatment_Group"], r["Time_Point"]): r["effect_size"] for r in rows}
    wk4_60 = [eff[(c, "60 mg QD", "week 4")] for c in ("ProtAge", "OrganAge_chrono", "ipfP3GPT", "PAOPAC")]
    assert round(-max(wk4_60), 2) == 2.71 and round(-min(wk4_60), 2) == 3.46, wk4_60    # "2.71 to 3.46 years" in [1]
    assert sum(r["p_value_corrected"] < 0.10 for r in rows) == 21                            # "21 of 54" in [1]
    return {"n_samples": 168, "change_sd": change_sd,
            "sample_sd": {c: round(float(cols[i].std(ddof=1)), 2) for i, c in enumerate(ORDER)},
            "corr": {a: {b: round(float(corr[i, j]), 2) for j, b in enumerate(ORDER)} for i, a in enumerate(ORDER)}}


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1]), indent=1))
