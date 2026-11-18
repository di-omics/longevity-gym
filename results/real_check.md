# The simulator's clock noise against real clock readouts

Real numbers: aggregates computed from the public supplementary tables of reference [1] in the README (an open access article, CC BY 4.0) by tools/real_targets.py. No participant-level data is in this repo. Simulated numbers: a fibrosis cohort given an inert compound. This compares noise only. It says nothing about any drug.

## Noise of a change score (years): SD of one person's change between two visits

| simulated clock | real clock it imitates | real estimate (5th to 95th percentile) | simulator, default | real / default | simulator, calibrated |
|---|---|---|---|---|---|
| prot_sparse_chrono | ProtAge | 2.03 (1.65 to 2.25) | 0.72 | 2.8 | 2.10 |
| prot_dense_chrono | OrganAge_chrono | 2.61 (2.09 to 2.99) | 0.44 | 6.0 | 2.76 |
| prot_dense_chrono_b | ipfP3GPT | 2.82 (2.24 to 3.24) | 0.43 | 6.6 | 2.92 |
| prot_organ_chrono | PAOPAC | 3.16 (2.54 to 3.53) | 0.75 | 4.2 | 3.27 |
| prot_sparse_mortality | OrganAge_mortality | 3.70 (3.01 to 4.12) | 1.36 | 2.7 | 3.80 |
| prot_age_mortality | PAC | 4.31 (3.48 to 4.91) | 1.42 | 3.0 | 4.39 |
| epi_chrono | none in [1] | assumed 2.65 | 0.49 | | 2.57 |
| epi_mortality | none in [1] | assumed 2.65 | 0.58 | | 2.64 |

The real estimate is indirect: it is backed out of published Mann-Whitney statistics under a normal model with one SD per clock, and visits there are 2 to 12 weeks apart. The calibrated column matches the real estimate by construction.

## Not used for calibration: SD of readings over samples (years)

| simulated clock | real clock | real, 168 samples | simulator, default | simulator, calibrated |
|---|---|---|---|---|
| prot_sparse_chrono | ProtAge | 5.0 | 6.7 | 6.8 |
| prot_dense_chrono | OrganAge_chrono | 5.1 | 6.5 | 6.8 |
| prot_dense_chrono_b | ipfP3GPT | 5.1 | 6.5 | 6.8 |
| prot_organ_chrono | PAOPAC | 5.7 | 6.7 | 7.0 |
| prot_sparse_mortality | OrganAge_mortality | 12.5 | 9.5 | 9.8 |
| prot_age_mortality | PAC | 13.6 | 9.5 | 10.1 |

## Not used for calibration: correlation between clocks over samples

Each cell: real / simulator default / simulator calibrated.

| | ProtAge | OrganAge_chrono | OrganAge_mortality | PAC | ipfP3GPT | PAOPAC |
|---|---|---|---|---|---|---|
| ProtAge | 1 | 0.87 / 0.98 / 0.95 | 0.51 / 0.97 / 0.94 | 0.48 / 0.96 / 0.93 | 0.82 / 0.98 / 0.95 | 0.90 / 1.00 / 0.96 |
| OrganAge_chrono | 0.87 / 0.98 / 0.95 | 1 | 0.27 / 0.96 / 0.93 | 0.27 / 0.95 / 0.92 | 0.89 / 1.00 / 0.96 | 0.79 / 0.98 / 0.94 |
| OrganAge_mortality | 0.51 / 0.97 / 0.94 | 0.27 / 0.96 / 0.93 | 1 | 0.94 / 0.98 / 0.94 | 0.35 / 0.96 / 0.93 | 0.55 / 0.97 / 0.93 |
| PAC | 0.48 / 0.96 / 0.93 | 0.27 / 0.95 / 0.92 | 0.94 / 0.98 / 0.94 | 1 | 0.34 / 0.95 / 0.92 | 0.56 / 0.96 / 0.91 |
| ipfP3GPT | 0.82 / 0.98 / 0.95 | 0.89 / 1.00 / 0.96 | 0.35 / 0.96 / 0.93 | 0.34 / 0.95 / 0.92 | 1 | 0.75 / 0.98 / 0.94 |
| PAOPAC | 0.90 / 1.00 / 0.96 | 0.79 / 0.98 / 0.94 | 0.55 / 0.97 / 0.93 | 0.56 / 0.96 / 0.91 | 0.75 / 0.98 / 0.94 | 1 |

Simulated samples are restricted to ages 55.5 to 78.5 so that the age spread is close to the real cohort's (SD 6.65 years).

## The one free choice: how much of the added noise the clocks share

The calibrated profile assumes 0.5. The open data cannot say. Reference reward and the gap to two shortcuts under calibrated noise, 600 seeds, for three values:

| share of added noise common to one modality | reference reward | one clock alone: gap (SE) | six proteomic clocks only: gap (SE) |
|---|---|---|---|
| 0.0 | 0.797 | +0.208 (0.015) | +0.074 (0.011) |
| 0.5 | 0.749 | +0.159 (0.014) | +0.132 (0.013) |
| 1.0 | 0.716 | +0.128 (0.014) | +0.153 (0.013) |
