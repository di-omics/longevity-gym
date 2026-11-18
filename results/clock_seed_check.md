# Do the clock sensitivities depend on the training seed?

Each clock refitted with training seeds 1, 2, 3, 4, 5. Cells give the lowest and highest value over those refits, in years. Last column: how many of the four shared proteins the clock uses.

| clock | per year of organ aging | per SD inflammation | per unit fibrosis activity | per SD cell mix | shared proteins used |
|---|---|---|---|---|---|
| prot_sparse_chrono | +0.79 to +0.80 | -0.04 to +0.03 | +2.10 to +2.18 | +0.00 to +0.00 | 4 |
| prot_dense_chrono | +0.80 to +0.81 | +0.02 to +0.11 | +0.64 to +0.83 | +0.00 to +0.00 | 3 to 4 |
| prot_sparse_mortality | +1.01 to +1.02 | +1.32 to +1.40 | +3.80 to +4.05 | +0.00 to +0.00 | 1 |
| prot_age_mortality | +1.03 to +1.06 | +1.22 to +1.40 | +3.97 to +4.21 | +0.00 to +0.00 | 1 |
| prot_dense_chrono_b | +0.80 to +0.81 | +0.02 to +0.08 | +0.62 to +0.82 | +0.00 to +0.00 | 4 |
| prot_organ_chrono | +0.80 to +0.80 | -0.05 to +0.00 | +2.09 to +2.15 | +0.00 to +0.00 | 4 |
| epi_chrono | +0.78 to +0.78 | +0.00 to +0.00 | +0.00 to +0.00 | -0.70 to -0.63 | 0 |
| epi_mortality | +1.11 to +1.12 | +0.00 to +0.00 | +0.00 to +0.00 | +0.09 to +0.14 | 0 |
