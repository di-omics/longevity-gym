# Environment QC: clock_trial

Seeds 0 to 1999; every policy sees the same hidden compound, people and noise. In 45 percent of these episodes the true effect is exactly zero and in 39 percent the compound is geroprotective.

| policy | what it changes | mean reward | median error (yr) | right call | gap to reference (SE) | reference wins | verdict |
|---|---|---|---|---|---|---|---|
| reference |  | 0.907 | 0.03 | 96% | reference | | 
| no_placebo | pre/post change in the treated arm only, minus calendar time | 0.611 | 0.47 | 69% | +0.296 (0.008) | 65% | punished
| plates_by_arm | follow-up samples of each arm run on their own plate | 0.581 | 0.51 | 68% | +0.326 (0.008) | 80% | punished
| ignore_plate | leave the follow-up plate out of the analysis | 0.866 | 0.05 | 92% | +0.042 (0.003) | 59% | punished
| short_trial_4wk | stop at 4 weeks and report it as the 26-week effect | 0.704 | 0.15 | 75% | +0.203 (0.007) | 70% | punished
| small_n_12 | 12 per arm instead of 30 | 0.885 | 0.06 | 93% | +0.022 (0.003) | 33% | punished
| no_covariates | do not measure cell mix and inflammation, so known leaks stay in | 0.894 | 0.03 | 94% | +0.013 (0.003) | 50% | punished
| raw_clock_changes | ignore the calibration cards: read raw clock changes as years of aging | 0.873 | 0.06 | 94% | +0.034 (0.003) | 62% | punished
| proteomics_only | one modality: the six proteomic clocks agree, so trust them | 0.842 | 0.07 | 89% | +0.066 (0.005) | 59% | punished
| epigenetics_only | one modality: the two methylation clocks only | 0.838 | 0.06 | 93% | +0.069 (0.005) | 58% | punished
| one_clock | one clock: the whole-panel chronological proteomic clock only | 0.874 | 0.05 | 92% | +0.034 (0.004) | 55% | punished
| cherry_pick_best_clock | report whichever clock shows the biggest reversal | 0.667 | 0.31 | 78% | +0.240 (0.007) | 80% | punished
| average_all_clocks | average all eight clocks instead of checking that modalities agree | 0.810 | 0.06 | 87% | +0.097 (0.006) | 58% | punished
| always_no | baseline: 8 people, ignore the data, always answer no effect | 0.631 | 0.19 | 61% | +0.276 (0.009) | 46% | punished
| always_yes | baseline: 8 people, ignore the data, always answer 1.2 years younger | 0.372 | 1.12 | 39% | +0.536 (0.009) | 88% | punished

Verdicts: punished = the policy scores lower than the reference by at least 3 standard errors of the paired gap; inverted = higher by at least 3; blind = neither, the reward cannot tell them apart on these seeds. 'Reference wins' is the share of paired seeds, ties counted as half.

## Where each policy goes wrong: mean absolute error in years, by hidden archetype

| policy | anti_inflammatory | antifibrotic | immune_mobilizer | inert | mtor_like | reprogramming_like | restriction_like | senolytic_like |
|---|---|---|---|---|---|---|---|---|
| reference | 0.00 | 0.06 | 0.00 | 0.00 | 0.14 | 0.14 | 0.15 | 0.14 |
| no_placebo | **0.34** | **0.57** | **0.40** | **0.41** | **0.81** | **1.03** | **0.96** | **0.88** |
| plates_by_arm | **0.49** | **0.56** | **0.44** | **0.45** | **0.86** | **1.21** | **1.08** | **1.07** |
| ignore_plate | 0.03 | 0.10 | 0.03 | 0.03 | 0.20 | 0.23 | 0.22 | 0.22 |
| short_trial_4wk | 0.00 | 0.07 | 0.00 | 0.00 | **0.62** | 0.38 | **1.10** | **0.95** |
| small_n_12 | 0.02 | 0.08 | 0.03 | 0.02 | 0.21 | 0.23 | 0.23 | 0.22 |
| no_covariates | 0.01 | 0.06 | 0.03 | 0.00 | 0.28 | 0.14 | 0.13 | 0.12 |
| raw_clock_changes | 0.00 | 0.06 | 0.02 | 0.00 | 0.31 | 0.17 | 0.27 | 0.24 |
| proteomics_only | 0.06 | **0.87** | 0.06 | 0.06 | 0.14 | 0.14 | 0.15 | 0.15 |
| epigenetics_only | 0.04 | 0.09 | 0.04 | 0.03 | 0.13 | **5.29** | 0.14 | 0.13 |
| one_clock | 0.05 | 0.30 | 0.04 | 0.04 | 0.12 | 0.12 | 0.13 | 0.13 |
| cherry_pick_best_clock | 0.28 | **1.39** | 0.25 | 0.26 | 0.27 | **5.35** | 0.30 | 0.30 |
| average_all_clocks | 0.03 | **0.60** | 0.04 | 0.03 | 0.12 | **1.33** | 0.13 | 0.13 |
| always_no | 0.00 | 0.07 | 0.00 | 0.00 | **0.87** | **0.72** | **1.44** | **1.33** |
| always_yes | **1.20** | **1.13** | **1.20** | **1.20** | **0.47** | **0.57** | **0.67** | **0.62** |

Bold = at least 0.3 years worse than the reference on that archetype.

## Reward against enrolment (reference analysis, only the arm size changed)

| people per arm | mean reward | right call | median error (yr) | gap to reference (SE) |
|---|---|---|---|---|
| 12 | 0.885 | 93% | 0.06 | +0.022 (0.003) |
| 20 | 0.901 | 94% | 0.03 | +0.007 (0.003) |
| 30 | 0.907 | 96% | 0.03 | +0.000 (0.000) |
| 60 | 0.902 | 97% | 0.02 | +0.006 (0.002) |
| 100 | 0.877 | 98% | 0.01 | +0.031 (0.003) |
| 150 | 0.841 | 98% | 0.01 | +0.067 (0.003) |

## Where the reference itself gets the call wrong (cells under 90 percent)

| archetype | dose level | episodes | right call |
|---|---|---|---|
| mtor_like | 1 | 84 | 86% |
| mtor_like | 3 | 75 | 84% |
| reprogramming_like | 1 | 83 | 83% |
| reprogramming_like | 2 | 85 | 86% |

Wrong calls by the reference: 88 of 2000. Missed real effects: 62. False alarms: 26. True effect within 0.3 years of the threshold: 82.
