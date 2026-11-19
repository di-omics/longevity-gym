<!-- README.md is generated from tools/README.template.md by tools/build_readme.py. Edit the template, then rebuild. -->
# longevity-gym

A simulated RL environment for one question: did this intervention make simulated people
biologically younger, or did it only move the clocks?

**Status: v0.1, simulation only.** Nothing here is trained on real data. The repo holds no real
proteomic or methylation data, no published clock, no participant-level trial data and no
stored model or agent. Two kinds of things are fitted, both at run time and both on simulated
data only: the eight small ridge regressions that serve as clocks, and the two small learned
policies of the shortcut check near the end. The only real numbers are a few aggregate
statistics computed from the open supplementary tables of [1]. They are used in one section,
to check the simulator's noise and to set one optional noise profile. Every other number is an
assumed default ([docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md)). Sister repo to
[drugdev-gym](https://github.com/di-omics/drugdev-gym): hidden truth, named mistakes, and a QC
card that says what the reward can and cannot see.

## Where things are

| I want to | Look here |
|---|---|
| see the task as an agent sees it, or run one episode | `longevity-gym spec`, `longevity-gym play --seed 3`, [env.py](src/longevitygym/env.py) |
| read how the simulated people and their omics are made | [biology.py](src/longevitygym/biology.py) |
| read how the clocks are fitted and what each one reads | [clocks.py](src/longevitygym/clocks.py), [results/clocks.md](results/clocks.md), [results/clock_seed_check.md](results/clock_seed_check.md) |
| see what each archetype does to each clock, next to the truth | [interventions.py](src/longevitygym/interventions.py), [readouts.py](src/longevitygym/readouts.py), [results/readouts.md](results/readouts.md) |
| read the scripted reference analysis and the named mistakes | [policies.py](src/longevitygym/policies.py) |
| read the QC card | [envqc.py](src/longevitygym/envqc.py), [results/qc_clock_trial.md](results/qc_clock_trial.md) |
| check whether a memorising policy beats the reference | [shortcut.py](src/longevitygym/shortcut.py), [results/shortcut.md](results/shortcut.md) |
| compare the simulator's noise with real clock readouts | [realcheck.py](src/longevitygym/realcheck.py), [tools/real_targets.py](tools/real_targets.py), [results/real_check.md](results/real_check.md) |
| find an assumed number and the module that holds it | [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) |
| find the command that writes each results file | [results/README.md](results/README.md) |
| change this README | [tools/README.template.md](tools/README.template.md), then [tools/build_readme.py](tools/build_readme.py) |
| find the test for a module | [tests/](tests): one file per module, plus test_repo.py for the repo's own rules |

This README is generated from [tools/README.template.md](tools/README.template.md). Edit the
template, not README.md.

## Run it

Needs Python 3.11 or newer.

```bash
pip install -e ".[dev]"
pytest -q
longevity-gym spec                        # the task as an agent sees it
longevity-gym play --seed 3               # one episode with the scripted reference
longevity-gym clocks                      # the clock table (add --out results to save it)
longevity-gym seedcheck                   # the same after refitting with other seeds
longevity-gym readouts                    # clocks vs truth
longevity-gym qc --out results            # the QC card, several minutes
longevity-gym shortcut --out results      # the memorising check, several minutes
longevity-gym realcheck --out results     # simulator noise against real clock readouts
longevity-gym qc --noise calibrated --out results   # the QC card under real-world noise
python -m longevitygym spec               # the same CLI without the console script
python tools/build_readme.py              # rebuild this README from results/
```

```python
from longevitygym import make
env = make(seed=0)
task = env.reset()
obs, _, _, _ = env.step({"n_per_arm": 30, "placebo": True, "weeks": 26})
_, reward, done, info = env.step({"effect_years": -0.3, "geroprotective": False})
```

Truth lives in the env object and is returned after the report. A harness for a real agent
must keep the agent on the JSON side and give it a new env for every episode. Numbers here
were generated with Python 3.12 and numpy 2 on macOS arm64; other builds can differ in the
last digit. If a run is much slower than stated (numpy built on OpenBLAS, for example numpy
1.26 from pip), set OPENBLAS_NUM_THREADS=1. After any change under src/, regenerate results/
and rebuild this README; a test fails if the README no longer matches results/.

## Why

In September 2026 a team from Insilico Medicine and several academic groups published an
exploratory analysis of a 12-week phase 2a trial of rentosertib in idiopathic pulmonary
fibrosis [1]. They ran six published proteomic aging clocks on serum from 42 participants and
compared each treated arm with placebo. Of 54 comparisons (6 clocks x 3 dose regimens x 3
visits), 21 showed a larger fall in predicted age than placebo (one-sided tests, false
discovery rate 0.10), 11 of them at week 4. The paper states the limit itself: proteomic clocks
alone cannot separate an effect on aging from the drug's antifibrotic effect, and that cannot
be settled inside a fibrosis cohort.

Two details in the paper shaped this simulator:

- all six clocks were trained on UK Biobank data from mostly healthy people and were then read
  in patients;
- a fibrosis-related protein (LTBP2) was the most important feature behind the shifts, and the
  only important feature present in all six clocks.

This repo does not analyze that trial. It uses none of its data and none of those clocks, and
nothing below says whether rentosertib, or any real drug, slows aging. It builds a toy world in
which the same kind of question has a known answer, so that a model can be scored on how it
reads a panel of clocks, and so that the reward can be checked before anyone scales it.

## How it works

1. **People** ([biology.py](src/longevitygym/biology.py)). Each simulated person has seven
   organ ages, systemic inflammation, fibrosis activity and a blood cell mix. Biological age is
   defined as the mean organ age. Inflammation, fibrosis activity and cell mix leak into the
   omics but, by this definition, are not aging.
2. **Omics.** 240 simulated protein features and 200 simulated methylation features, with
   plate effects. They are unnamed numbers with assumed loadings, not real proteins or CpG
   sites. Four lung-enriched proteins are coded to be the strongest and least noisy age markers
   in healthy people and to rise with fibrosis activity as well. They stand in for the shared
   fibrosis-related feature reported in [1]. Fibrosis activity also nudges every other
   organ-enriched protein in its own "older" direction, so in this toy world the disease looks
   like aging across the proteome.
3. **Clocks** ([clocks.py](src/longevitygym/clocks.py)). Eight ridge regressions fitted to
   simulated people. Six imitate the training recipes of the six clocks in [1] as far as a
   small linear model can. Two methylation clocks are this repo's addition; the study in [1]
   used proteomic clocks only. Each clock comes with a calibration card: how far its reading
   moves per year of true organ aging and per unit of two measurable covariates, in healthy
   people. How a clock reads disease is not on its card.
4. **Interventions** ([interventions.py](src/longevitygym/interventions.py)). Eight abstract
   archetypes at three dose levels, each with two hidden potency multipliers (0.25 to 1.75), so
   the true effect is a continuous number. Some are coded to change organ aging. Some only
   change what leaks into a clock. The agent sees a code name, never the mechanism.
5. **Environment** ([env.py](src/longevitygym/env.py)). `clock_trial`, two steps: design a
   trial (arm size, placebo, duration, plate layout, covariates, which clocks), receive
   per-sample clock readings, then report the effect in years at 26 weeks. The report also
   carries a yes or no on geroprotective (half a year or more younger), which must agree with
   the number. Reward = half for the estimate, half for the call, minus enrolment cost. One env
   object is one episode.
6. **Environment QC** ([envqc.py](src/longevitygym/envqc.py)). A scripted reference analysis,
   twelve named mistakes that each change one thing, and two constant-answer baselines, all run
   on the same seeds, people and noise.

## The eight simulated clocks

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

How to read this table:

- **None of these is a real clock.** All eight rows are ridge regressions on simulated
  features. r and MAE are measured on held-out simulated people (chronological clocks against
  age, mortality clocks against the noisy risk score they were trained on). They are not
  accuracy figures for any published clock.
- **"Recipe borrowed from"** names the published clock whose training recipe the row imitates:
  what is predicted (chronological age, or a mortality-risk score), who it is fitted on (a
  mostly healthy general population for all six, as in [1]), roughly what goes in, and that
  each clock is fitted on its own part of one shared pool of people. The model class is not
  imitated. The originals are gradient-boosted trees [2][6], elastic nets [3], a Cox model
  followed by a Gompertz model [4] and a neural network [5]. Everything here is linear.
- **The last four columns are the point of the table.** They give the change in the clock's
  reading, in years, when one hidden quantity is moved in simulated healthy people and
  everything else is held fixed. The agent is given three of them as the clock's calibration
  card. The fibrosis column is withheld: in this toy world, as in [1], the clocks were never
  characterised in patients.
- "Per SD" means per unit of the simulator's own scale for inflammation and cell mix. One unit
  is the SD of the person-to-person noise term. Across a whole simulated population the SD is
  about 1.1 units, so per population SD the readings are about a tenth larger.

What the simulated clocks read:

- All of them follow organ aging, at 0.78 to 1.11 years per year. The
  chronological clocks under-read a real change by about a fifth.
- The two proteomic mortality clocks read one unit of inflammation as about 1.4
  years. The chronological clocks and both methylation clocks do not (0.03 at
  most).
- **All six simulated proteomic clocks read fibrosis activity as age**, from 0.71 to
  4.20 years per unit. Each uses at least one of the four shared proteins, and
  fibrosis also nudges the rest of the proteome in the "older" direction. This is built in. The
  two whole-panel
  clocks read it least: 4 percent of their simulated training population carried some fibrosis
  activity, and a whole-panel fit learns to discount part of it. Fitted on healthy people only,
  the same two clocks read fibrosis about twice as strongly (a test checks this).
- The two methylation clocks read no fibrosis at all, which is also built in: in this simulator
  blood methylation does not see fibrosis activity.
- The chronological methylation clock reads the blood cell mix (-0.66 years
  per unit).

Refitting the clocks with five other training seeds gives the same picture
([results/clock_seed_check.md](results/clock_seed_check.md)). The fibrosis column ranges over
2.10 to 2.18 and 2.09 to 2.15 for the two
short-list chronological clocks, 0.64 to 0.83 and
0.62 to 0.82 for the two whole-panel ones, and
3.80 to 4.05 and 3.97 to 4.21 for the two
mortality clocks.

Where each recipe departs from its original:

| simulated clock | original, as described in its own paper | not imitated here |
|---|---|---|
| prot_sparse_chrono | ProtAge [2]: gradient-boosted trees on 204 proteins selected from 2,897 | the model class and the selection method |
| prot_dense_chrono | the conventional chronological model of [3], called OrganAge_chrono in [1]: an elastic net trained on the whole panel | the penalty; here the weakest fifth of the features is dropped |
| prot_sparse_mortality | the conventional mortality model of [3], called OrganAge_mortality in [1]: a Cox elastic net trained on the whole panel | survival modelling; here a linear fit to a made-up risk score on 12 proteins picked one at a time |
| prot_age_mortality | PAC [4]: chronological age plus 128 proteins, a Cox step and then a Gompertz model | survival modelling |
| prot_dense_chrono_b | the clock that [1] calls ipfP3GPT, described in [5] as a pathway-aware proteomic aging clock (in [5] the name ipf-P3GPT belongs to a separate transformer): a neural network on the whole panel with a branch for fibrosis-related pathways, trained on UK Biobank data | the network and its pathway design; this row is a second whole-panel fit and behaves like prot_dense_chrono |
| prot_organ_chrono | PAOPAC [6]: a family of gradient-boosted clocks, one conventional clock that starts from all plasma proteins and 14 organ proxy clocks built from organ-enriched marker panels | the organ proxy structure; here one clock on 16 organ-panel proteins. [1] does not say which PAOPAC model it ran. If it was the conventional clock, this row imitates the family's organ proxy recipe and not the model that was run |

In [1] the name OrganAge refers to the models of [3]. A different, SomaScan-based package with
the same name exists (Oh et al., Nature 2023) and is not what [1] used.

## What each simulated clock says, next to the simulated truth

Years, treated minus placebo, 26 weeks, dose level 2, nominal potency, 150 per arm, mean of 20
simulated trials. TRUTH = change in mean organ age. Bold = the printed value is 0.5 years or
more away from the printed truth. Not evidence about any real clock, drug or trial. Fibrosis
cohort shown; the healthy cohort is in [results/readouts.md](results/readouts.md).

| archetype | TRUTH | prot_sparse_chrono | prot_dense_chrono | prot_sparse_mortality | prot_age_mortality | prot_dense_chrono_b | prot_organ_chrono | epi_chrono | epi_mortality |
|---|---|---|---|---|---|---|---|---|---|
| inert | +0.0 | +0.0 | +0.0 | +0.0 | -0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| antifibrotic | -0.1 | **-1.7** | **-0.6** | **-3.3** | **-3.7** | **-0.7** | **-1.7** | -0.1 | -0.1 |
| anti_inflammatory | +0.0 | -0.0 | -0.0 | **-1.4** | **-1.4** | -0.0 | +0.0 | +0.0 | +0.0 |
| senolytic_like | -1.4 | -1.1 | -1.1 | **-1.9** | **-2.0** | -1.1 | -1.1 | -1.1 | -1.5 |
| mtor_like | -1.2 | -0.9 | -0.9 | -1.1 | -1.2 | -0.9 | -0.9 | **-0.6** | -1.3 |
| reprogramming_like | -0.8 | -0.6 | -0.6 | -0.8 | -0.8 | -0.6 | -0.6 | **-5.3** | **-7.5** |
| immune_mobilizer | +0.0 | +0.0 | +0.0 | +0.0 | -0.0 | +0.0 | +0.0 | **-1.3** | +0.3 |
| restriction_like | -1.6 | -1.3 | -1.3 | -2.0 | **-2.1** | -1.3 | -1.3 | -1.3 | -1.8 |

- **In this simulator a compound that treats the disease moves every proteomic clock.** The
  antifibrotic archetype takes 0.1 years off mean organ age (one organ, the
  lung). The six proteomic clocks report 0.6 to 3.7 years
  younger. The two methylation clocks report 0.1 and 0.1 years younger. In the healthy cohort the same
  archetype has nothing to act on and no clock moves.
- **The two proteomic mortality clocks read lower inflammation as younger.** The
  anti-inflammatory archetype changes no organ. Both report about 1.4 years
  younger. The chronological clocks and both methylation clocks stay near zero.
- **The simulated methylation clocks can be moved directly.** The reprogramming-like archetype
  takes 0.8 years off organ age and 5.3 to 7.5
  years off the two methylation clocks. The proteomic clocks stay near the truth.
- **A cell-mix shift moves the simulated chronological methylation clock** by 1.3
  years with no organ change.
- Four archetypes are coded to make every organ younger. At the dose level shown, three of them
  (senolytic-like, mTOR-like, restriction-like) move all eight clocks in the same direction;
  the fourth, reprogramming-like, is the one above. This does not hold at every dose: at dose
  level 3 the mTOR-like archetype also shifts the blood cell mix, and the chronological
  methylation clock then reads older while the other seven read younger. Which archetypes
  "work" is a coding choice. It is not evidence about senolytics, mTOR inhibitors, dietary
  restriction or reprogramming.

These patterns were coded into the simulator or follow from fitting linear clocks to it. The
table shows what this simulator's clocks read under each coded mechanism. It is not evidence
about any real clock, drug or trial, and it must not be used to read the result in [1] in
either direction. The antifibrotic archetype is not a model of rentosertib: its small effect on
organ age is a number chosen for this simulator.

## Environment QC (2000 seeds)

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

### Where each policy goes wrong: mean absolute error in years, by hidden archetype

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

### Reward against enrolment (reference analysis, only the arm size changed)

| people per arm | mean reward | right call | median error (yr) | gap to reference (SE) |
|---|---|---|---|---|
| 12 | 0.885 | 93% | 0.06 | +0.022 (0.003) |
| 20 | 0.901 | 94% | 0.03 | +0.007 (0.003) |
| 30 | 0.907 | 96% | 0.03 | +0.000 (0.000) |
| 60 | 0.902 | 97% | 0.02 | +0.006 (0.002) |
| 100 | 0.877 | 98% | 0.01 | +0.031 (0.003) |
| 150 | 0.841 | 98% | 0.01 | +0.067 (0.003) |

### Where the reference itself gets the call wrong (cells under 90 percent)

| archetype | dose level | episodes | right call |
|---|---|---|---|
| mtor_like | 1 | 84 | 86% |
| mtor_like | 3 | 75 | 84% |
| reprogramming_like | 1 | 83 | 83% |
| reprogramming_like | 2 | 85 | 86% |

Wrong calls by the reference: 88 of 2000. Missed real effects: 62. False alarms: 26. True effect within 0.3 years of the threshold: 82.

What the card says:

- The reference analysis lands within 0.03 years on the median and makes the
  right call 96 percent of the time on these seeds. It is a first draft and
  a floor, not an optimum. Treat the second decimal of every figure on this card as noise: on
  another block of seeds the smallest gaps can change verdict.
- The costliest choices are running each arm's follow-up samples on its own plate (0.33 reward
  lost), having no placebo arm (0.30), reporting the best-looking clock (0.24) and stopping at 4
  weeks (0.20).
- **Trusting the six proteomic clocks because they agree** loses 0.07
  overall, and in this simulator it is wrong where it matters. On the antifibrotic archetype
  its error is 0.87 years against
  0.06 for the reference. The six simulated clocks agree there because
  they were built to share inputs and a training population. That is a property of this toy
  world. It is not a finding about the six real clocks or about the trial in [1].
- Methylation alone loses 0.07: it over-reads the reprogramming-like
  archetype by 5.29 years. Averaging all eight clocks is
  still off by 1.33 years there.
- **One clock is not enough either.** Using the whole-panel chronological proteomic clock alone,
  with its calibration card, loses 0.03 (SE 0.004). It is the proteomic clock that reads
  fibrosis least, and it is still fooled on the antifibrotic archetype: its error there is 0.30
  years against 0.06 for the reference.
- Also punished, by less: leaving the plate out of the analysis (gap +0.042, SE 0.003);
  enrolling 12 per arm instead of 30 (gap +0.022, SE 0.003); not measuring the two covariates
  (gap +0.013, SE 0.003); ignoring the calibration cards (gap +0.034, SE 0.003).

- No cell of the reference is under 70 percent right calls on these seeds. The table above lists
  the cells under 90 percent.
- Of the reference's 88 wrong calls, 62 are real effects called not geroprotective and 26 are
  false alarms. In 82 of the 88 the true effect is within 0.3 years of the half-year threshold.
- The reward has a high floor. Answering "no effect" without looking scores
  0.63, because 45 percent of the hidden compounds do nothing.
  Read every reward above against that floor.
- The cost term is steep. Under the reference analysis the reward is highest at
  30 people per arm on this grid, and 150 per arm (0.84) scores
  lower than 12 per arm (0.89) although it makes the right call more often
  (98 against 93 percent). That is a property of one assumed cost
  constant, not a statement about trial economics.

## Can a policy that memorises beat the reference?

Trained on seeds 20000 to 22399. Each cell: mean reward, then the paired difference to the reference on the same seeds (standard error). Positive = beats the reference. In the last column the hidden aging potency is forced to 2.5, outside the range of 0.25 to 1.75 that the policies were trained on.

| policy | trial design | seeds 0 to 399 | seeds 1000 to 1399 | seeds 1000 to 1399, aging potency 2.5 |
|---|---|---|---|---|
| reference | reference design | 0.905 | 0.908 | 0.911 |
| memoriser | same design as the reference | 0.824, -0.081 (0.011) | 0.846, -0.062 (0.011) | 0.751, -0.160 (0.011) |
| classify_regress | same design as the reference | 0.896, -0.009 (0.008) | 0.908, -0.000 (0.008) | 0.914, +0.003 (0.005) |
| memoriser | 12 per arm | 0.824, -0.081 (0.012) | 0.857, -0.051 (0.011) | 0.764, -0.147 (0.011) |
| classify_regress | 12 per arm | 0.878, -0.027 (0.010) | 0.900, -0.009 (0.010) | 0.898, -0.013 (0.006) |
| memoriser | no placebo arm | 0.726, -0.179 (0.016) | 0.736, -0.172 (0.017) | 0.685, -0.226 (0.015) |
| classify_regress | no placebo arm | 0.731, -0.174 (0.016) | 0.740, -0.168 (0.017) | 0.697, -0.214 (0.015) |
| memoriser | stop at 4 weeks | 0.792, -0.113 (0.012) | 0.812, -0.096 (0.013) | 0.733, -0.178 (0.012) |
| classify_regress | stop at 4 weeks | 0.837, -0.068 (0.011) | 0.855, -0.054 (0.011) | 0.837, -0.074 (0.008) |
| memoriser | plates by arm | 0.661, -0.244 (0.018) | 0.706, -0.202 (0.017) | 0.654, -0.257 (0.015) |
| classify_regress | plates by arm | 0.673, -0.232 (0.018) | 0.707, -0.201 (0.017) | 0.660, -0.251 (0.015) |

Two learned policies, refitted on every run from 2,400 episodes with only what an agent
legitimately gets ([shortcut.py](src/longevitygym/shortcut.py)):

- **Pure memorising.** Recognising the archetype and answering with a memorised effect scores
  0.824 and 0.846 on two blocks of new seeds, against 0.905 and 0.908 for the reference. Pooled
  over the two blocks the difference is -0.071 (SE 0.007): memorising loses.
- **Learning inside the task mix.** Recognising the archetype and then estimating inside it
  scores 0.896 and 0.908. Pooled difference to the reference: -0.005 (SE 0.006): a tie within
  the noise.
- **Outside the potency range they were trained on** (aging potency forced to 2.5) the memoriser
  scores 0.751 and the learner 0.914, against 0.911 for the reference (differences -0.160, SE
  0.011, and +0.003, SE 0.005). The memoriser falls behind the reference; the learner stays
  level with the reference. A policy that reads the clocks should not care about the range, so
  this column is the one to watch when a stronger learner is trained here.
- **The design lessons still cost the learner.** Against its own full design, taking away the
  placebo arm costs it 0.165, stopping at 4 weeks 0.059 and putting each arm on its own plate
  0.222 on the first block (0.168, 0.054 and 0.201 on the second). Enrolling 12 per arm instead
  of 30 changes its score by -0.018 and -0.009.

Seeds are public, and the task text alone (compound code, dose level, cohort) is enough to
identify most development seeds. Treat seeds 0 to 1999 as a development set, and
score a trained agent on seeds drawn at evaluation time from a range too large to enumerate.

## How far is the simulator from real clock readouts?

The supplementary tables of [1] are public (the article is open access, CC BY 4.0). They list
clock predictions for 168 samples with no participant, arm or visit label, and summary
statistics for every arm and visit. A few aggregates were computed from them with
[tools/real_targets.py](tools/real_targets.py). No participant-level data is in this repo, and
the samples were not linked back to participants. The full comparison is in
[results/real_check.md](results/real_check.md). It compares noise and agreement between clocks
only, and says nothing about any drug.

- **The simulator is far too quiet.** For the six real clocks in that trial's patients, one
  person's change between two visits has an SD of about 2.0 to 4.3 years. That covers everything
  that makes two visits differ: assay noise, short-term biology and, in the treated arms,
  differences in response. The estimate is indirect: it is backed out of the paper's published
  test statistics. The simulator's default is 2.7 to 6.6 times smaller.
- **Simulated clocks agree with each other far more than real ones.** Over samples, the four
  real chronological clocks correlate 0.75 to 0.90 with each other and 0.27 to 0.56 with the two
  mortality clocks. In the simulator those correlations are 0.98 to 1.00 and 0.95 to 0.97, and
  calibrating the noise only brings them to 0.94 to 0.96 and 0.91 to 0.94. Real patients differ
  along more dimensions than these simulated ones, and no noise setting fixes that.
- **With real-world noise the task is much harder.** `make(seed, noise="calibrated")` adds
  reading noise to every clock until its change-score SD matches the real estimate. Under it the
  reference analysis scores 0.74 instead of 0.91 and makes the right call 82 percent of the time
  instead of 96, at 30 per arm. At 150 per arm it makes the right call 91 percent of the time,
  and on the enrolment grid the reward is highest at 100 per arm. The full card is in
  [results/qc_clock_trial_calibrated.md](results/qc_clock_trial_calibrated.md).
- Under calibrated noise 10 of the 12 named mistakes are still punished. The reward can no
  longer tell the reference from: leaving the plate out of the analysis (gap +0.010, SE 0.004);
  ignoring the calibration cards (gap +0.001, SE 0.003).
- Two things in the calibrated profile are assumptions, not measurements. First, half of the
  added noise is shared by the clocks of one modality in a sample. That choice matters: using
  one clock alone loses 0.21 if none of the noise is shared, 0.16 at one half and 0.13 if all of
  it is (600 seeds, SE about 0.01). Second, the two methylation clocks, for which [1] has no
  data, get the mean target of the four chronological proteomic clocks.

Every other section of this README uses the default noise. Read those results as statements
about the logic of reading a panel of clocks, not about how large a real trial has to be.

## Limits

- "Biological age = mean organ age" is a definition made for this simulator. The field has no
  agreed ground truth, which is the reason to simulate one.
- Effect sizes are placeholders chosen so that each failure mode is visible. They are not
  estimates for any real drug, diet or procedure, and nothing here says any intervention works.
- The clocks are linear fits to simulated features. They imitate training recipes, not models.
  No published weight, protein list or dataset is used.
- The reference analysis leans on one assumption: that blood methylation does not see fibrosis
  activity at all. If it did, checking one modality against the other would protect less.
  Nothing here tests that assumption, and [1] had no second modality to check against.
- The default noise is several times lower than that of real clocks, and the simulated clocks
  agree with each other far more than real ones do (see the section on real clock readouts).
- A score on this version does not separate reading the clocks from knowing this simulator's
  task mix (eight archetypes, one potency range). The off-range column of the shortcut table
  is a first step; a held-out archetype is needed as well.
- The reference analysis and the list of mistakes are a first draft, and no one outside has
  reviewed them.
- One environment, one disease cohort, two modalities. Next: transcriptomic and blood
  chemistry clocks, a layer that replays real public clock readouts, and an LLM-agent harness.
- No licence has been chosen yet, so for now all rights are reserved.

## References

[1] Zhavoronkov A. et al. Integration of proteomic aging clocks in a phase 2a clinical trial
supports simultaneous geroprotective assessment. Nature Biotechnology (2026).
doi:10.1038/s41587-026-03286-y. Open access.

[2] Argentieri M.A. et al. Proteomic aging clock predicts mortality and risk of common
age-related diseases in diverse populations. Nature Medicine 30, 2450-2460 (2024).
doi:10.1038/s41591-024-03164-7.

[3] Goeminne L.J.E. et al. Plasma protein-based organ-specific aging and mortality models
unveil diseases as accelerated aging of organismal systems. Cell Metabolism 37, 205-222 (2025).
doi:10.1016/j.cmet.2024.10.005.

[4] Kuo C.-L. et al. Proteomic aging clock (PAC) predicts age-related outcomes in middle-aged
and older adults. Aging Cell 23, e14195 (2024). doi:10.1111/acel.14195.

[5] Galkin F. et al. AI-driven toolset for IPF and aging research associates lung fibrosis with
accelerated aging. Aging (Albany NY) 17, 1999-2014 (2025). doi:10.18632/aging.206295. The
description of the clock above follows the preprint, doi:10.1101/2025.01.09.632065.

[6] Xu H. et al. Proteome-aware organ proxy aging clocks. bioRxiv (2026).
doi:10.64898/2026.04.24.720503. A preprint, not peer reviewed.
