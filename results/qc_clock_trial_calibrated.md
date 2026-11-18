# Environment QC: clock_trial (calibrated noise)

Seeds 0 to 1999; every policy sees the same hidden compound, people and noise. In 45 percent of these episodes the true effect is exactly zero and in 39 percent the compound is geroprotective.

| policy | what it changes | mean reward | median error (yr) | right call | gap to reference (SE) | reference wins | verdict |
|---|---|---|---|---|---|---|---|
| reference |  | 0.740 | 0.24 | 82% | reference | | 
| no_placebo | pre/post change in the treated arm only, minus calendar time | 0.600 | 0.51 | 68% | +0.141 (0.009) | 51% | punished
| plates_by_arm | follow-up samples of each arm run on their own plate | 0.571 | 0.57 | 67% | +0.169 (0.009) | 67% | punished
| ignore_plate | leave the follow-up plate out of the analysis | 0.730 | 0.25 | 81% | +0.010 (0.004) | 53% | blind
| short_trial_4wk | stop at 4 weeks and report it as the 26-week effect | 0.630 | 0.32 | 68% | +0.110 (0.006) | 59% | punished
| small_n_12 | 12 per arm instead of 30 | 0.693 | 0.32 | 76% | +0.047 (0.007) | 40% | punished
| no_covariates | do not measure cell mix and inflammation, so known leaks stay in | 0.730 | 0.25 | 80% | +0.010 (0.003) | 49% | punished
| raw_clock_changes | ignore the calibration cards: read raw clock changes as years of aging | 0.739 | 0.23 | 81% | +0.001 (0.003) | 48% | blind
| proteomics_only | one modality: the six proteomic clocks agree, so trust them | 0.605 | 0.50 | 72% | +0.135 (0.007) | 69% | punished
| epigenetics_only | one modality: the two methylation clocks only | 0.610 | 0.51 | 76% | +0.130 (0.007) | 70% | punished
| one_clock | one clock: the whole-panel chronological proteomic clock only | 0.585 | 0.57 | 72% | +0.155 (0.008) | 70% | punished
| cherry_pick_best_clock | report whichever clock shows the biggest reversal | 0.355 | 1.18 | 48% | +0.385 (0.011) | 80% | punished
| average_all_clocks | average all eight clocks instead of checking that modalities agree | 0.636 | 0.43 | 76% | +0.104 (0.007) | 67% | punished
| always_no | baseline: 8 people, ignore the data, always answer no effect | 0.631 | 0.19 | 61% | +0.109 (0.009) | 34% | punished
| always_yes | baseline: 8 people, ignore the data, always answer 1.2 years younger | 0.372 | 1.12 | 39% | +0.369 (0.012) | 74% | punished

Verdicts: punished = the policy scores lower than the reference by at least 3 standard errors of the paired gap; inverted = higher by at least 3; blind = neither, the reward cannot tell them apart on these seeds. 'Reference wins' is the share of paired seeds, ties counted as half.

## Where each policy goes wrong: mean absolute error in years, by hidden archetype

| policy | anti_inflammatory | antifibrotic | immune_mobilizer | inert | mtor_like | reprogramming_like | restriction_like | senolytic_like |
|---|---|---|---|---|---|---|---|---|
| reference | 0.17 | 0.23 | 0.13 | 0.13 | 0.43 | 0.50 | 0.52 | 0.50 |
| no_placebo | 0.37 | **0.57** | 0.39 | **0.46** | **0.82** | **1.07** | **1.01** | **0.92** |
| plates_by_arm | **0.51** | **0.57** | **0.44** | **0.46** | **0.94** | **1.21** | **1.16** | **1.10** |
| ignore_plate | 0.18 | 0.24 | 0.15 | 0.15 | 0.44 | 0.51 | 0.55 | 0.53 |
| short_trial_4wk | 0.17 | 0.21 | 0.13 | 0.13 | 0.69 | 0.50 | **1.22** | **1.08** |
| small_n_12 | 0.25 | 0.29 | 0.23 | 0.23 | 0.61 | 0.63 | 0.70 | 0.70 |
| no_covariates | 0.17 | 0.23 | 0.15 | 0.13 | 0.47 | 0.50 | 0.51 | 0.48 |
| raw_clock_changes | 0.15 | 0.21 | 0.12 | 0.11 | 0.46 | 0.44 | 0.54 | 0.50 |
| proteomics_only | **0.54** | **1.10** | **0.51** | **0.55** | 0.53 | 0.56 | 0.51 | 0.59 |
| epigenetics_only | **0.51** | 0.50 | **0.49** | **0.53** | 0.51 | **5.27** | 0.54 | 0.50 |
| one_clock | **0.67** | **0.67** | **0.63** | **0.66** | 0.67 | 0.67 | 0.60 | 0.69 |
| cherry_pick_best_clock | **1.10** | **2.06** | **1.04** | **1.11** | **1.05** | **5.60** | **0.96** | **1.09** |
| average_all_clocks | 0.42 | **0.84** | 0.39 | 0.39 | 0.43 | **1.36** | 0.42 | 0.47 |
| always_no | 0.00 | 0.07 | 0.00 | 0.00 | **0.87** | 0.72 | **1.44** | **1.33** |
| always_yes | **1.20** | **1.13** | **1.20** | **1.20** | 0.47 | 0.57 | 0.67 | 0.62 |

Bold = at least 0.3 years worse than the reference on that archetype.

## Reward against enrolment (reference analysis, only the arm size changed)

| people per arm | mean reward | right call | median error (yr) | gap to reference (SE) |
|---|---|---|---|---|
| 12 | 0.693 | 76% | 0.32 | +0.047 (0.007) |
| 20 | 0.722 | 80% | 0.28 | +0.018 (0.006) |
| 30 | 0.740 | 82% | 0.24 | +0.000 (0.000) |
| 60 | 0.769 | 86% | 0.16 | -0.028 (0.006) |
| 100 | 0.774 | 90% | 0.11 | -0.033 (0.006) |
| 150 | 0.752 | 91% | 0.08 | -0.012 (0.006) |

## Where the reference itself gets the call wrong (cells under 90 percent)

| archetype | dose level | episodes | right call |
|---|---|---|---|
| anti_inflammatory | 2 | 100 | 89% |
| antifibrotic | 1 | 70 | 87% |
| antifibrotic | 2 | 81 | 80% |
| antifibrotic | 3 | 81 | 89% |
| mtor_like | 1 | 84 | 74% |
| mtor_like | 2 | 96 | 76% |
| mtor_like | 3 | 75 | 59% |
| reprogramming_like | 1 | 83 | 54% |
| reprogramming_like | 2 | 85 | 66% |
| reprogramming_like | 3 | 69 | 71% |
| restriction_like | 1 | 91 | 57% |
| restriction_like | 2 | 65 | 71% |
| restriction_like | 3 | 89 | 88% |
| senolytic_like | 1 | 81 | 68% |
| senolytic_like | 2 | 84 | 88% |
| senolytic_like | 3 | 86 | 80% |

Wrong calls by the reference: 361 of 2000. Missed real effects: 227. False alarms: 134. True effect within 0.3 years of the threshold: 163.
