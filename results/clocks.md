| clock | target | inputs | recipe borrowed from (not the model) | r | MAE (yr) | per year of organ aging | per SD inflammation | per unit fibrosis activity | per SD cell mix |
|---|---|---|---|---|---|---|---|---|---|
| prot_sparse_chrono | chronological | 17 proteins selected for their correlation with age | ProtAge [2] | 0.89 | 3.2 | +0.79 | +0.08 | +1.35 | +0.00 |
| prot_dense_chrono | chronological | the whole panel, weakest fifth of the proteins dropped | conventional chronological model of [3] (OrganAge_chrono in [1]) | 0.90 | 3.1 | +0.81 | +0.04 | +0.24 | +0.00 |
| prot_sparse_mortality | mortality | 12 proteins selected stepwise from the whole panel | conventional mortality model of [3] (OrganAge_mortality in [1]) | 0.92 | 3.6 | +1.01 | +1.41 | +2.13 | +0.00 |
| prot_age_mortality | mortality | chronological age plus 11 proteins selected stepwise | PAC [4] | 0.92 | 3.7 | +0.99 | +1.43 | +1.35 | +0.00 |
| prot_dense_chrono_b | chronological | all 240 proteins | ipfP3GPT [5] | 0.90 | 3.1 | +0.81 | +0.04 | +0.34 | +0.00 |
| prot_organ_chrono | chronological | 16 proteins drawn from organ-enriched panels | PAOPAC [6] | 0.89 | 3.2 | +0.79 | +0.04 | +1.43 | +0.00 |
| epi_chrono | chronological | all 200 methylation sites | none (this repo's addition) | 0.90 | 3.0 | +0.78 | +0.00 | +0.00 | -0.67 |
| epi_mortality | mortality | all 200 methylation sites | none (this repo's addition) | 0.92 | 3.5 | +1.11 | +0.00 | +0.00 | +0.13 |
