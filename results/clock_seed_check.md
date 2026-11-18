# Do the clock sensitivities depend on the training seed?

Each clock refitted with training seeds 1, 2, 3, 4, 5. Cells give the lowest and highest value over those refits, in years. Last column: how many of the four shared proteins the clock uses.

| clock | per year of organ aging | per SD inflammation | per unit fibrosis activity | per SD cell mix | shared proteins used |
|---|---|---|---|---|---|
| prot_sparse_chrono | +0.79 to +0.79 | +0.01 to +0.09 | +1.35 to +1.41 | +0.00 to +0.00 | 4 |
| prot_dense_chrono | +0.80 to +0.81 | +0.03 to +0.11 | +0.20 to +0.36 | +0.00 to +0.00 | 3 to 4 |
| prot_sparse_mortality | +1.00 to +1.01 | +1.36 to +1.47 | +1.24 to +2.17 | +0.00 to +0.00 | 1 to 2 |
| prot_age_mortality | +0.98 to +1.02 | +1.24 to +1.42 | +1.16 to +2.15 | +0.00 to +0.00 | 1 to 2 |
| prot_dense_chrono_b | +0.80 to +0.81 | +0.03 to +0.09 | +0.23 to +0.36 | +0.00 to +0.00 | 4 |
| prot_organ_chrono | +0.79 to +0.80 | -0.01 to +0.05 | +1.39 to +1.44 | +0.00 to +0.00 | 4 |
| epi_chrono | +0.78 to +0.78 | +0.00 to +0.00 | +0.00 to +0.00 | -0.69 to -0.63 | 0 |
| epi_mortality | +1.11 to +1.12 | +0.00 to +0.00 | +0.00 to +0.00 | +0.09 to +0.14 | 0 |
