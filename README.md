# longevity-gym

An RL environment for one question: did this intervention make people biologically younger,
or did it only move the clock?

**Status: v0.1, simulation only.** No real omics data, no real compounds, no medical claims.
Every number is an assumed default ([docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md)). Sister repo to
[drugdev-gym](https://github.com/di-omics/drugdev-gym) and built the same way: hidden truth,
named mistakes, and a QC card that says what the reward can and cannot see.

## Why

In 2026 Insilico Medicine reported running six proteomic aging clocks (ProtAge, two OrganAge
variants, PAC, ipfP3GPT and PAOPAC) on serum from a phase 2a trial of rentosertib in idiopathic
pulmonary fibrosis. All six trended younger in treated patients [1]. The obvious question, raised
in the coverage and acknowledged by the authors, is whether that is slower aging or a treated lung.

No real dataset can settle that, because nobody knows a patient's true biological age. A
simulator can at least make the question trainable: here the truth is known by construction, so
a model can be scored on whether it reads a panel of clocks correctly, and the reward itself
can be checked before anyone scales it.

## How it works

1. **People** ([biology.py](src/longevitygym/biology.py)). Each simulated person has seven organ
   ages, systemic inflammation, disease activity and a blood cell mix. Biological age is defined
   as the mean organ age. Inflammation, disease and cell mix travel with age and leak into the
   omics, but by definition they are not aging.
2. **Omics.** A 240-protein serum panel (organ-enriched, inflammation and disease proteins) and
   a 200-site blood methylation panel (age sites and cell-mix sites), with plate batch effects.
3. **Clocks** ([clocks.py](src/longevitygym/clocks.py)). Eight clocks trained on a simulated
   reference cohort, the way real clocks are trained. Six are analogs of the six proteomic clock
   families above: they share what was trained on what (chronological age or mortality, general
   population or a fibrosis cohort, all proteins or organ-enriched or sparse), not the models.
   Training targets follow the coverage in [1]. Two things are assumptions of this repo and
   not facts about the originals: that the fifth clock was trained in fibrosis patients (read
   from its name), and the sparse feature set of the sixth (chosen so the six recipes differ).
   Two methylation clocks add a second, independent modality.
4. **Interventions** ([interventions.py](src/longevitygym/interventions.py)). Eight abstract
   archetypes at three dose levels. Some change organ aging. Some only change what leaks into a
   clock. The agent sees a code name, never the mechanism.
5. **Environment** ([env.py](src/longevitygym/env.py)). `clock_trial`, two steps: design a trial
   (arm size, placebo, duration, batch layout, covariates, which clocks), receive per-sample
   clock readings, then report the effect in years at 26 weeks and a yes or no on geroprotective.
   Reward = half for the estimate, half for the call, minus enrolment cost.
6. **Environment QC** ([envqc.py](src/longevitygym/envqc.py)). A scripted expert, ten named
   mistakes that each change one thing, and two constant-answer baselines, all on the same seeds.

## The clocks

| clock | family | target | trained on | analog of | features | r | MAE (yr) |
|---|---|---|---|---|---|---|---|
| prot_chrono | proteomic | chronological | general | ProtAge (chronological) | 240 | 0.979 | 3.31 |
| organ_chrono | proteomic | chronological | general | OrganAge, chronological variant | 175 | 0.979 | 3.29 |
| organ_mortality | proteomic | mortality | general | OrganAge, mortality variant | 175 | 0.998 | 1.21 |
| prot_mortality | proteomic | mortality | general | PAC (mortality) | 240 | 0.997 | 1.25 |
| fibrosis_chrono | proteomic | chronological | fibrosis | ipfP3GPT (assumed trained in fibrosis) | 240 | 0.974 | 4.02 |
| sparse_chrono | proteomic | chronological | general | PAOPAC (chronological) | 30 | 0.978 | 3.36 |
| epi_chrono | epigenetic | chronological | general | first-generation methylation clock | 200 | 0.979 | 3.30 |
| epi_mortality | epigenetic | mortality | general | second-generation methylation clock | 200 | 0.994 | 1.86 |

r and MAE are against each clock's own training target, on a held-out healthy cohort.

## What each clock says, next to the truth

Years, treated minus placebo, 26 weeks, dose level 2, fibrosis cohort, 150 per arm, mean of 20 simulated trials. Bold = off by 0.5 years or more. Healthy cohort: [results/readouts.md](results/readouts.md).

| intervention | TRUTH | prot_chrono | organ_chrono | organ_mortality | prot_mortality | fibrosis_chrono | sparse_chrono | epi_chrono | epi_mortality |
|---|---|---|---|---|---|---|---|---|---|
| inert | +0.0 | +0.0 | +0.0 | +0.1 | -0.0 | +0.1 | +0.0 | +0.0 | +0.0 |
| antifibrotic | -0.1 | **+0.8** | +0.0 | -0.4 | -0.3 | **-1.3** | -0.1 | -0.1 | -0.1 |
| anti_inflammatory | +0.0 | **+0.8** | **+0.6** | **-1.2** | **-1.7** | **+0.8** | +0.2 | +0.0 | +0.0 |
| senolytic_like | -1.4 | -1.0 | -1.1 | -1.8 | **-2.1** | **-0.8** | -1.2 | -1.2 | -1.4 |
| mtor_like | -1.2 | -1.1 | -1.1 | -1.1 | -1.2 | -0.9 | -1.1 | -0.7 | -1.3 |
| reprogramming_like | -0.8 | -0.7 | -0.8 | -0.7 | -0.8 | -0.6 | -0.7 | **-6.1** | **-7.0** |
| immune_mobilizer | +0.0 | +0.0 | +0.0 | +0.1 | -0.0 | +0.1 | +0.0 | **-1.3** | +0.4 |
| restriction_like | -1.6 | -1.3 | -1.4 | -1.9 | **-2.1** | **-1.0** | -1.4 | -1.4 | -1.6 |

Reading the table:

- **A clock trained in the disease reads the disease.** The antifibrotic takes 0.1 years off
  mean organ age (one organ, the lung). The fibrosis-trained clock reports 1.3 years.
- **Mortality clocks read inflammation as age.** The anti-inflammatory changes no organ. Both
  proteomic mortality clocks report 1.2 to 1.7 years younger, and three of the four
  chronological proteomic clocks report 0.6 to 0.8 years OLDER. Opposite signs across training
  targets are the tell.
- **Methylation clocks can be moved directly.** The reprogramming-like archetype takes 0.8
  years off organ age and 6 to 7 years off both methylation clocks. The proteomic clocks stay
  near the truth.
- **A cell-mix shift moves a first-generation methylation clock** by 1.3 years with no organ
  change at all.
- Real effects (senolytic-like, mTOR-like, restriction-like) move all eight clocks together,
  within about half a year of the truth except the cells in bold.

These patterns exist because the simulator was built with them. The table shows what a clock
panel looks like under each mechanism, not what happened in any real trial.

## Environment QC (400 seeds)

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

### Where each mistake bites: mean absolute error in years, by hidden intervention

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

What the card says:

- The expert rule (drop the clock trained in the disease, take the median within each modality,
  believe the more conservative modality, zero if they disagree in sign) lands within 0.1 years
  on the median and makes the right call 93% of the time.
- Reporting the best-looking clock is the costliest analysis mistake: 0.45 years of median
  error and the right call 72% of the time. It is worst exactly where a clock can be moved
  without aging.
- One modality is not enough. Methylation alone over-reads the reprogramming-like archetype by
  5.6 years. Averaging all clocks is still off by 1.5 years there.
- No placebo arm and batching by arm each cost about 0.3 reward.
- **Blind spots, reported and not hidden.** The reward cannot see a 12-per-arm trial (it is
  cheaper, and wins 54% of paired seeds against the expert) and cannot see skipping the
  covariates (the cross-modality rule already protects the expert). No verdict is "clean":
  every mistake is punished on average, none reliably per episode.
- The reward has a high floor. Answering "no effect" without looking scores 0.56, because about
  half the hidden compounds do nothing. Read every reward above against that floor.

## Run it

```bash
pip install -e ".[dev]"
pytest -q
longevity-gym spec        # the task as an agent sees it
longevity-gym play --seed 3 --policy expert
longevity-gym readouts    # clocks vs truth, results/readouts.md
longevity-gym qc          # the card above, results/qc_clock_trial.md
```

```python
from longevitygym import make
env = make(seed=0)
task = env.reset()
obs, _, _, _ = env.step({"n_per_arm": 60, "placebo": True, "weeks": 26, "measure_covariates": True})
_, reward, done, info = env.step({"effect_years": -0.3, "geroprotective": False})
```

Truth lives in the env object. A harness for a real agent must keep the agent on the JSON side.

## Limits

- "Biological age = mean organ age" is a definition made for this simulator. The field has no
  agreed ground truth, which is the reason to simulate one.
- Effect sizes are placeholders chosen so each failure mode is visible. They are not estimates
  for any real drug, diet or procedure, and nothing here says any intervention works.
- The clocks are ridge regressions on simulated features. They are analogs of published clock
  families by training recipe only.
- The expert policy and the list of mistakes are a first draft and have had no outside review.
- One environment, one disease cohort, two modalities. Transcriptomic and blood chemistry
  clocks, real public cohorts to fit the loadings, and an LLM-agent harness are next.

## Reference

[1] Zhavoronkov A. et al., "Integration of proteomic aging clocks in a phase 2a clinical trial
supports simultaneous geroprotective assessment", Nature Biotechnology (2026),
doi:10.1038/s41587-026-03286-y. The description above is taken from press coverage
(News-Medical, 7 Sep 2026), not from the paper itself. Check the paper before quoting it.
