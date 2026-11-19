"""clocks.py: the eight simulated clocks and what each one reads."""
import numpy as np

from longevitygym.biology import KIND_SHARED, PANEL
from longevitygym.clocks import CLOCK_NAMES, EPIGENETIC, PROTEOMIC, clock_table, clocks


def test_eight_clocks_six_proteomic_two_methylation():
    assert len(CLOCK_NAMES) == 8 and len(PROTEOMIC) == 6 and len(EPIGENETIC) == 2
    targets = [clocks()[c].target for c in PROTEOMIC]
    assert targets.count("chronological") == 4 and targets.count("mortality") == 2


def test_clocks_track_their_targets_on_held_out_people():
    for row in clock_table():
        assert row["r"] > 0.85, row["clock"]
        assert 0.6 < row["per_year_organ_aging"] < 1.3, row["clock"]


def test_every_proteomic_clock_uses_a_shared_protein_and_reads_fibrosis_as_age():
    shared = set(np.flatnonzero(PANEL.prot_kind == KIND_SHARED))
    table = {r["clock"]: r for r in clock_table()}
    for name in PROTEOMIC:
        assert shared & set(clocks()[name].features), name
        assert table[name]["per_unit_fibrosis"] > 0.1, name
    for name in EPIGENETIC:
        assert abs(table[name]["per_unit_fibrosis"]) < 0.05, name


def test_whole_panel_clocks_discount_fibrosis_because_a_few_training_people_had_it():
    from longevitygym.clocks import train_clocks
    shipped = {r["clock"]: r["per_unit_fibrosis"] for r in clock_table()}
    healthy = {r["clock"]: r["per_unit_fibrosis"] for r in clock_table(train_clocks(population="none"))}
    for name in ("prot_dense_chrono", "prot_dense_chrono_b"):
        assert healthy[name] > 1.7 * shipped[name], name
        assert shipped[name] < min(shipped[c] for c in PROTEOMIC if "dense" not in c), name


def test_mortality_clocks_read_inflammation_and_chronological_ones_do_not():
    table = {r["clock"]: r for r in clock_table()}
    for name in PROTEOMIC:
        reads = table[name]["per_sd_inflammation"]
        assert (reads > 1.0) if clocks()[name].target == "mortality" else (abs(reads) < 0.3), name
