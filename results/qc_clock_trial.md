# Environment QC: clock_trial

Seeds 0 to 399, every policy on the same hidden truth.

| policy | mistake | mean reward | median error (yr) | call accuracy | win rate of expert | Z' | verdict |
|---|---|---|---|---|---|---|---|
| expert |  | 0.838 | 0.09 | 93% | reference | | 
| no_placebo | pre/post change in the treated arm only, minus calendar time | 0.575 | 0.50 | 64% | 64% | -5.32 | weak
| batch_by_arm | follow-up samples of each arm run in their own batch | 0.528 | 0.69 | 64% | 78% | -4.30 | weak
| no_covariates | no blood cell mix or inflammation marker, so no adjustment | 0.832 | 0.09 | 92% | 54% | -186.88 | blind
| short_trial_4wk | stop at 4 weeks and report it as the 26-week effect | 0.592 | 0.31 | 64% | 75% | -5.59 | weak
| small_n_12 | 12 per arm | 0.793 | 0.18 | 85% | 46% | -28.38 | blind
| proteomics_only | one modality: the six proteomic clocks only | 0.803 | 0.15 | 92% | 65% | -30.76 | weak
| epigenetics_only | one modality: the two methylation clocks only | 0.740 | 0.17 | 89% | 67% | -12.54 | weak
| trust_disease_clock | headline the clock trained in the disease being treated | 0.675 | 0.31 | 82% | 81% | -7.44 | weak
| cherry_pick_best_clock | report whichever clock shows the biggest reversal | 0.558 | 0.45 | 72% | 83% | -4.38 | weak
| average_all_clocks | average every clock instead of checking that modalities agree | 0.773 | 0.15 | 91% | 67% | -17.77 | weak
| null | smallest trial, ignore the data, always answer: no effect | 0.563 | 0.39 | 52% | 50% | -5.70 | weak
| always_yes | smallest trial, ignore the data, always answer: 1.2 years younger | 0.438 | 0.87 | 48% | 80% | -3.03 | weak

Verdicts: clean = Z' >= 0.5; visible = expert wins >= 90% of paired seeds; weak = wins 60 to 90% or mean gap >= 0.1; blind = neither; inverted = the mistake wins.

## Where each mistake bites: mean absolute error in years, by hidden intervention

| policy | anti_inflammatory | antifibrotic | immune_mobilizer | inert | mtor_like | reprogramming_like | restriction_like | senolytic_like |
|---|---|---|---|---|---|---|---|---|
| expert | 0.06 | 0.07 | 0.11 | 0.04 | 0.26 | 0.16 | 0.19 | 0.20 |
| no_placebo | 0.25 | **0.42** | **0.43** | **0.37** | **0.86** | **1.24** | **0.90** | **0.87** |
| batch_by_arm | **0.45** | **0.59** | **0.58** | **0.37** | **0.80** | **0.99** | **1.13** | **1.07** |
| no_covariates | 0.09 | 0.07 | 0.06 | 0.04 | 0.24 | 0.16 | 0.21 | 0.23 |
| short_trial_4wk | 0.06 | 0.09 | 0.11 | 0.04 | **0.69** | 0.43 | **1.19** | **0.99** |
| small_n_12 | 0.13 | 0.18 | 0.13 | 0.08 | 0.36 | 0.38 | 0.41 | 0.37 |
| proteomics_only | 0.21 | 0.19 | 0.32 | 0.17 | 0.24 | 0.16 | 0.19 | 0.19 |
| epigenetics_only | 0.22 | 0.16 | 0.36 | 0.17 | 0.22 | **5.62** | 0.15 | 0.15 |
| trust_disease_clock | 0.33 | **0.83** | **0.49** | 0.27 | 0.35 | 0.32 | 0.38 | 0.45 |
| cherry_pick_best_clock | **0.66** | **0.83** | **0.72** | 0.31 | 0.35 | **6.03** | 0.35 | 0.38 |
| average_all_clocks | 0.15 | 0.16 | 0.25 | 0.12 | 0.20 | **1.47** | 0.14 | 0.13 |
| null | 0.00 | 0.08 | 0.00 | 0.00 | **0.92** | **0.75** | **1.61** | **1.35** |
| always_yes | **1.20** | **1.12** | **1.20** | **1.20** | 0.28 | 0.45 | **0.65** | 0.44 |

Bold = at least 0.3 years worse than the expert on that intervention.
