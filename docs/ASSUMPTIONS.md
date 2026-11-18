# Assumptions

Every number in this simulator is an assumed default. None is fitted to data. The ones that
drive the results are listed here so that each can be challenged, replaced by a measured value,
or randomized. Anything not listed is in the source.

## People (biology.py)

| quantity | value | note |
|---|---|---|
| organs | immune, liver, kidney, vascular, lung, brain, muscle | biological age = their mean, a definition made for this simulator |
| shared aging offset per person | SD 4 years | all organs older or younger together |
| organ-specific offset | SD 3 years | |
| inflammation | 0.05 SD per year of age and 0.05 SD per year of shared offset, unit noise | so it tracks biological age. If the two coefficients differ, chronological clocks pick up an inflammation weight whose sign depends on which is larger |
| blood cell mix | -0.05 SD per year of age, unit noise | lymphoid share falls with age |
| fibrosis activity, fibrosis cohort | 0.8 plus 0.02 per year of age over 60, noise SD 0.3, at least 0.1 | adds 0.5 SD of inflammation per unit; does not change organ age |
| fibrosis activity, general population | 4 percent of people carry 0.2 to 1.2 units | the "mostly healthy" training population |
| mortality-risk score | age + 1.2 x weighted organ gap + 1.5 x inflammation + 3.0 x fibrosis activity | organ weights 1.5, 1.0, 1.3, 1.5, 1.0, 0.8, 0.9 (normalized). No deaths are simulated |
| trial participants | ages 45 to 80 | clocks are trained on ages 40 to 70 |

## Omics

The features are unnamed simulated numbers, not real proteins or CpG sites.

| quantity | value |
|---|---|
| proteins (240) | 25 per organ (175), 20 inflammation, 12 fibrosis only, 33 uninformative |
| organ-enriched proteins | 0.3 to 1.0 per decade of that organ's age, random sign |
| shared proteins | 4 of the 25 lung-enriched proteins: 1.0 to 1.2 per decade of lung age (rising), 0.6 to 1.2 per unit of fibrosis activity, and 0.3 times the person offset and measurement noise of the other proteins |
| every other organ-enriched protein | 0 to 0.15 per unit of fibrosis activity, each in its own "older" direction: about one apparent year of aging per unit, with no change in organ age |
| inflammation proteins | 0.6 to 1.0 per SD of inflammation |
| fibrosis-only proteins | 0.6 to 1.2 per unit of fibrosis activity |
| background loadings | every protein also carries inflammation (SD 0.03) and fibrosis (SD 0.02) |
| methylation sites (200) | 120 age sites (0.3 to 1.0 per decade of mean organ age, random sign, plus a cell-mix loading of SD 0.1), 40 cell-mix sites (0.5 to 1.0 per SD), 40 uninformative |
| methylation and disease | methylation does not see fibrosis or inflammation at all. The reference analysis depends on this |
| person offsets | SD 0.5 (protein), 0.4 (methylation), stable across visits |
| measurement noise | SD 0.3 (protein), 0.25 (methylation) |
| plates | baseline samples on plate 0, follow-up samples on plates 1 and 2 |
| plate effect | random per feature (SD 0.25 protein, 0.12 methylation) plus a shift along the aging direction equal to aging every organ by SD 1.5 years (protein) or 1.2 years (methylation) |

## Clocks (clocks.py)

All eight are ridge regressions on standardized features with penalty 1, which at this sample
size is close to least squares. One pool of 40,000 simulated people aged 40 to 70 from the
general population; each clock is fitted on its own random 80 percent of the pool. Mortality
clocks are fitted to the mortality-risk score plus noise of SD 4 years, standing for risk the
omics cannot see. Training seed 20261118.

| clock | inputs |
|---|---|
| prot_sparse_chrono | the 17 proteins most correlated with age |
| prot_dense_chrono | the whole panel, then the weakest fifth by coefficient size dropped and refitted |
| prot_sparse_mortality | 12 proteins picked one at a time: each step takes the protein most correlated with what the current fit leaves unexplained |
| prot_age_mortality | chronological age plus 11 proteins picked the same way |
| prot_dense_chrono_b | all 240 proteins |
| prot_organ_chrono | 16 organ-enriched proteins: the best 2 per organ plus the best 2 of the rest |
| epi_chrono, epi_mortality | all 200 methylation sites |

The subset sizes follow the originals only loosely (7 percent of the panel for the ProtAge
recipe, about 5 percent for the two mortality recipes) and are otherwise my choice.

Calibration cards. For every clock the agent is told three numbers, measured in simulated
healthy people with everything else held fixed: years of reading per year of true organ aging,
per unit of the cell mix covariate and per unit of the inflammation covariate. How a clock
reads fibrosis activity is not on its card.

## Interventions (interventions.py)

Abstract archetypes. Which of them change organ aging is a coding choice, not evidence about
any real intervention. Shifts below are at full onset, dose level 2 and potency 1.

| archetype | organ aging (years) | not aging |
|---|---|---|
| inert | 0 | none |
| antifibrotic | lung -1.0, only in the fibrosis cohort | fibrosis activity -0.8, inflammation -0.3 |
| anti_inflammatory | 0 | inflammation -1.0 SD |
| senolytic_like | all organs -1.5 | inflammation -0.4 |
| mtor_like | all organs -1.2 | cell mix -0.45 SD |
| reprogramming_like | all organs -0.8 | methylation readout rewound 6 years |
| immune_mobilizer | 0 | cell mix +2.0 SD |
| restriction_like | all organs -1.8 | inflammation -0.3 |

| quantity | value |
|---|---|
| dose levels 1, 2, 3 | scale every effect by 0.5, 1.0, 1.3. Exception, mtor_like: aging 0.6, 1.0, 0.6 and cell mix 0, -0.45, -1.8 SD |
| hidden potency | two multipliers per episode, each uniform 0.25 to 1.75: one for the aging effect, one for everything else |
| fibrosis and inflammation | linked at baseline only (0.5 SD per unit). During a trial a change in fibrosis activity does not move inflammation; the antifibrotic's -0.3 is a separate assumed number |
| onset | aging effects and the methylation rewind build with a time constant of 6 to 12 weeks; the rest in 1.5 weeks |
| individual response | SD 30 percent, one multiplier per person for all of the compound's effects |
| change between visits without treatment | calendar time, plus organ age SD 0.15 years, inflammation SD 0.5, cell mix SD 0.4; fibrosis progresses 0.004 units per week |
| covariates | blood cell mix and an inflammation marker, each with measurement noise SD 0.3 |
| geroprotective | 0.5 years or more off mean organ age at 26 weeks, versus placebo |

## Task mix and reward (env.py)

Each seed draws one of 8 archetypes, one of 2 cohorts and one of 3 dose levels with equal
probability, then the two potencies. The QC card states how many of its episodes have a true
effect of exactly zero and how many are geroprotective.

Reward = 0.5 x exp(-|error| / 0.75 years) + 0.5 x (call correct) - cost, with cost 0.05 per 120
enrolled people. The QC card shows the consequences: a constant "no effect" answer already
scores well above zero, the reward peaks at a small trial, and a very large trial scores lower
than a very small one.

## Reference analysis (policies.py)

30 per arm with placebo, 26 weeks, follow-up plates randomized, covariates measured. Reports
under 0.2 years are rounded to exactly zero. The arm size of 30 was picked from the enrolment
curve on the QC card's own seeds, so the card flatters it slightly. The zero band of 0.2 years
was set by hand.
