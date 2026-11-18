# The eight simulated clocks

All eight rows are ridge regressions on simulated features. None is a real clock. The fourth column names the published clock whose training recipe the row imitates; no published model, weight or protein list is used. r and MAE are measured on held-out simulated people and are not accuracy figures for any published clock. Numbers in square brackets refer to the reference list in README.md.

| clock | target | inputs | recipe borrowed from (not the model) | r | MAE (yr) | per year of organ aging | per SD inflammation | per unit fibrosis activity | per SD cell mix |
|---|---|---|---|---|---|---|---|---|---|
| prot_sparse_chrono | chronological | 17 proteins selected for their correlation with age | ProtAge [2] | 0.89 | 3.2 | +0.79 | +0.02 | +2.10 | +0.00 |
| prot_dense_chrono | chronological | the whole panel, weakest fifth of the proteins dropped | conventional chronological model of [3] (OrganAge_chrono in [1]) | 0.90 | 3.1 | +0.81 | +0.03 | +0.71 | +0.00 |
| prot_sparse_mortality | mortality | 12 proteins selected stepwise from the whole panel | conventional mortality model of [3] (OrganAge_mortality in [1]) | 0.92 | 3.6 | +1.02 | +1.39 | +3.78 | +0.00 |
| prot_age_mortality | mortality | chronological age plus 11 proteins selected stepwise | PAC [4] | 0.92 | 3.6 | +1.03 | +1.39 | +4.20 | +0.00 |
| prot_dense_chrono_b | chronological | all 240 proteins | ipfP3GPT [5] | 0.90 | 3.1 | +0.81 | +0.03 | +0.79 | +0.00 |
| prot_organ_chrono | chronological | 16 proteins drawn from organ-enriched panels | PAOPAC [6] | 0.89 | 3.2 | +0.80 | -0.02 | +2.13 | +0.00 |
| epi_chrono | chronological | all 200 methylation sites | none (this repo's addition) | 0.90 | 3.0 | +0.78 | +0.00 | +0.00 | -0.66 |
| epi_mortality | mortality | all 200 methylation sites | none (this repo's addition) | 0.92 | 3.5 | +1.11 | +0.00 | +0.00 | +0.13 |
