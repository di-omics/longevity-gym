# Environment QC: clock_trial

Seeds 0 to 999; every policy sees the same hidden compound, people and noise.

| policy | what it changes | mean reward | median error (yr) | right call | gap to reference (SE) | reference wins | verdict |
|---|---|---|---|---|---|---|---|
| reference |  | 0.860 | 0.09 | 93% | reference | | 
| no_placebo | pre/post change in the treated arm only, minus calendar time | 0.593 | 0.48 | 65% | +0.267 (0.011) | 67% | punished
| plates_by_arm | follow-up samples of each arm run on their own plate | 0.567 | 0.55 | 64% | +0.292 (0.012) | 75% | punished
| ignore_plate | leave the follow-up plate out of the analysis | 0.825 | 0.12 | 89% | +0.035 (0.005) | 59% | punished
| short_trial_4wk | stop at 4 weeks and report it as the 26-week effect | 0.648 | 0.19 | 68% | +0.212 (0.009) | 72% | punished
| small_n_12 | 12 per arm instead of 30 | 0.839 | 0.12 | 89% | +0.021 (0.005) | 43% | punished
| proteomics_only | one modality: the six proteomic clocks agree, so trust them | 0.816 | 0.15 | 90% | +0.043 (0.007) | 64% | punished
| epigenetics_only | one modality: the two methylation clocks only | 0.750 | 0.15 | 84% | +0.110 (0.009) | 64% | punished
| one_clock | one clock: the whole-panel chronological proteomic clock only | 0.860 | 0.12 | 94% | -0.001 (0.005) | 63% | blind
| cherry_pick_best_clock | report whichever clock shows the biggest reversal | 0.468 | 0.76 | 59% | +0.391 (0.014) | 84% | punished
| average_all_clocks | average all eight clocks instead of checking that modalities agree | 0.764 | 0.18 | 86% | +0.095 (0.009) | 66% | punished
| always_no | baseline: 8 people, ignore the data, always answer no effect | 0.602 | 0.23 | 57% | +0.257 (0.012) | 51% | punished
| always_yes | baseline: 8 people, ignore the data, always answer 1.2 years younger | 0.402 | 1.09 | 43% | +0.458 (0.014) | 80% | punished

Verdicts: punished = the policy scores lower than the reference by at least 3 standard errors of the paired gap; inverted = higher by at least 3; blind = neither, the reward cannot tell them apart on these seeds. 'Reference wins' is the share of paired seeds, ties counted as half.

## Where each policy goes wrong: mean absolute error in years, by hidden archetype

| policy | anti_inflammatory | antifibrotic | immune_mobilizer | inert | mtor_like | reprogramming_like | restriction_like | senolytic_like |
|---|---|---|---|---|---|---|---|---|
| reference | 0.03 | 0.06 | 0.06 | 0.04 | 0.29 | 0.17 | 0.26 | 0.23 |
| no_placebo | 0.32 | **0.46** | 0.35 | **0.40** | **0.85** | **0.95** | **0.95** | **0.87** |
| plates_by_arm | **0.43** | **0.52** | **0.46** | **0.40** | **0.88** | **1.02** | **1.10** | **1.01** |
| ignore_plate | 0.06 | 0.11 | 0.09 | 0.05 | 0.33 | 0.22 | 0.32 | 0.28 |
| short_trial_4wk | 0.03 | 0.07 | 0.06 | 0.04 | **0.70** | 0.43 | **1.11** | **0.97** |
| small_n_12 | 0.05 | 0.10 | 0.08 | 0.06 | 0.35 | 0.24 | 0.30 | 0.28 |
| proteomics_only | 0.16 | **0.49** | 0.12 | 0.14 | 0.18 | 0.17 | 0.25 | 0.21 |
| epigenetics_only | 0.10 | 0.10 | **0.50** | 0.11 | 0.26 | **4.98** | 0.13 | 0.14 |
| one_clock | 0.11 | 0.14 | 0.09 | 0.09 | 0.15 | 0.15 | 0.27 | 0.24 |
| cherry_pick_best_clock | **1.43** | **1.07** | **1.23** | **0.35** | 0.35 | **5.97** | **0.56** | **0.71** |
| average_all_clocks | **0.35** | **0.38** | 0.16 | 0.13 | 0.17 | **1.17** | 0.15 | 0.15 |
| always_no | 0.00 | 0.08 | 0.00 | 0.00 | **0.86** | **0.72** | **1.48** | **1.35** |
| always_yes | **1.20** | **1.12** | **1.20** | **1.20** | 0.42 | **0.51** | **0.57** | 0.52 |

Bold = at least 0.3 years worse than the reference on that archetype.

## Reward against enrolment (reference analysis, only the arm size changed)

| people per arm | mean reward | right call | median error (yr) | gap to reference (SE) |
|---|---|---|---|---|
| 12 | 0.839 | 89% | 0.12 | +0.021 (0.005) |
| 20 | 0.854 | 92% | 0.11 | +0.005 (0.004) |
| 30 | 0.860 | 93% | 0.09 | +0.000 (0.000) |
| 60 | 0.846 | 94% | 0.08 | +0.014 (0.003) |
| 100 | 0.817 | 94% | 0.07 | +0.043 (0.004) |
| 150 | 0.782 | 95% | 0.06 | +0.077 (0.004) |

## Where the reference itself gets the call wrong (cells under 90 percent)

| archetype | dose level | episodes | right call |
|---|---|---|---|
| mtor_like | 1 | 45 | 78% |
| mtor_like | 2 | 49 | 86% |
| mtor_like | 3 | 33 | 45% |
| reprogramming_like | 1 | 40 | 80% |
| reprogramming_like | 2 | 33 | 79% |
| reprogramming_like | 3 | 40 | 85% |
| restriction_like | 1 | 48 | 81% |
| senolytic_like | 1 | 40 | 80% |

Wrong calls by the reference: 74 of 1000. Missed real effects: 70. False alarms: 4. True effect within 0.3 years of the threshold: 61.
