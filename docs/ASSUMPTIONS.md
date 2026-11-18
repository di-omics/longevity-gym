# Assumptions

Every number in this package is an assumed default. None is fitted to data. They are listed
here so that each one can be challenged, replaced by a measured value, or randomized.

## People (biology.py)

| quantity | value | note |
|---|---|---|
| organs | immune, liver, kidney, vascular, lung, brain, muscle | biological age = their mean |
| shared aging offset per person | SD 4 years | all organs older or younger together |
| organ-specific offset | SD 3 years | |
| inflammation | 0.03 SD per year of age, 0.08 SD per year of shared offset, unit noise | |
| blood cell mix | -0.05 SD per year of age, unit noise | lymphoid share falls with age |
| fibrosis: disease activity | about 0.8 units, rising 0.02 per year of age | adds 4 lung-years and 0.5 SD inflammation per unit |
| mortality target | age + 1.2 x weighted organ gap + 1.5 x inflammation + 3 x disease + noise SD 4 | what mortality clocks are trained on |

## Omics

| quantity | value |
|---|---|
| proteins | 25 per organ (175), 20 inflammation, 20 disease, 25 uninformative |
| lung proteins | also carry up to 0.3 of the disease signal |
| methylation sites | 120 age sites, 40 cell-mix sites, 40 uninformative |
| person offsets | SD 0.5 (protein), 0.4 (methylation), stable across visits |
| measurement noise | SD 0.3 (protein), 0.25 (methylation) |
| batch effect | random per feature (SD 0.25 and 0.12) plus a component along the aging axis worth roughly 1 to 2 clock-years per plate |

## Clocks

Ridge regression (penalty 50) on standardized features. Reference cohort: 3000 people aged 20
to 90. Fibrosis cohort: 800 people aged 45 to 85. The sparse clock keeps the 30 features most
correlated with age.

## Interventions

Abstract archetypes. Full-onset shifts at dose level 2; levels 1 and 3 scale by 0.5 and 1.3
unless stated. Aging effects build with a time constant of 6 to 12 weeks (the methylation rewind builds at the
same rate), the rest in 1.5 weeks. Untreated fibrosis progresses 0.004 disease units per week.
Individual response varies with SD 30%.

| archetype | organ aging (years) | not aging |
|---|---|---|
| inert | 0 | none |
| antifibrotic | lung -1.0, only in fibrosis | disease -0.8, inflammation -0.3 |
| anti_inflammatory | 0 | inflammation -1.0 SD |
| senolytic_like | all organs -1.5 | inflammation -0.4 |
| mtor_like | all organs -1.2 (0.6x at levels 1 and 3) | cell mix -0.45 SD at level 2, -1.8 at level 3 |
| reprogramming_like | all organs -0.8 | methylation readout rewound 6 years |
| immune_mobilizer | 0 | cell mix +2.0 SD |
| restriction_like | all organs -1.8 | inflammation -0.3 |

Geroprotective = 0.5 years or more off mean organ age at 26 weeks, versus placebo.

## Reward

0.5 x exp(-|error| / 0.75 years) + 0.5 x (call correct) - enrolment cost (0.05 per 120 people).
Half of the hidden compounds have no effect, so a constant answer scores about 0.5.
