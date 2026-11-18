# longevity-gym

A simulated RL environment for one question: did this intervention make simulated people
biologically younger, or did it only move the clocks?

**Status: v0.1, simulation only.** Nothing here is trained on real data. The repo holds no real
proteomic or methylation data, no published clock, no trial data and no trained agent. The only
things fitted are eight small ridge regressions on simulated people. Every number is an assumed
default ([docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md)). Sister repo to
[drugdev-gym](https://github.com/di-omics/drugdev-gym): hidden truth, named mistakes, and a QC
card that says what the reward can and cannot see.

## Why

In September 2026 a team from Insilico Medicine and several academic groups published an
exploratory analysis of a 12-week phase 2a trial of rentosertib in idiopathic pulmonary
fibrosis [1]. They ran six published proteomic aging clocks on serum from 42 participants and
compared each treated arm with placebo. Of 54 comparisons (6 clocks x 3 dose regimens x 3
visits), 21 showed a lower predicted age at a false discovery rate of 0.10, 11 of them at week
4. The paper states the limit itself: proteomic clocks alone cannot separate an effect on aging
from the drug's antifibrotic effect, and that cannot be settled inside a fibrosis cohort.

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
   sites. Four lung-enriched proteins are coded to be strong age markers in healthy people and
   to rise with fibrosis activity as well. They stand in for the shared fibrosis-related
   feature reported in [1].
3. **Clocks** ([clocks.py](src/longevitygym/clocks.py)). Eight ridge regressions fitted to
   simulated people. Six imitate the training recipes of the six clocks in [1] as far as a
   small linear model can. Two methylation clocks are this repo's addition; the study in [1]
   used proteomic clocks only.
4. **Interventions** ([interventions.py](src/longevitygym/interventions.py)). Eight abstract
   archetypes at three dose levels, each with two hidden potency multipliers, so the true
   effect is a continuous number. Some are coded to change organ aging. Some only change what
   leaks into a clock. The agent sees a code name, never the mechanism.
5. **Environment** ([env.py](src/longevitygym/env.py)). `clock_trial`, two steps: design a
   trial (arm size, placebo, duration, plate layout, covariates, which clocks), receive
   per-sample clock readings, then report the effect in years at 26 weeks. The report also
   carries a yes or no on geroprotective (half a year or more younger), which must agree with
   the number. Reward = half for the estimate, half for the call, minus enrolment cost. One env
   object is one episode.
6. **Environment QC** ([envqc.py](src/longevitygym/envqc.py)). A scripted reference analysis,
   ten named mistakes that each change one thing, and two constant-answer baselines, all run on
   the same seeds, people and noise.

## The eight simulated clocks

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
  everything else is held fixed.

What the simulated clocks read:

- All of them follow organ aging, at 0.78 to 1.11 years per year. The
  chronological clocks under-read a real change by about a fifth.
- The two proteomic mortality clocks read one SD of inflammation as about 1.4 years.
  The chronological clocks do not (0.08 at most).
- **All six proteomic clocks read fibrosis activity as age**, from 0.24 to
  2.13 years per unit, because each of them uses at least one of the four shared
  proteins. This is built in. The two methylation clocks read none of it, which is also built
  in: in this simulator blood methylation does not see the lung.
- The chronological methylation clock reads the blood cell mix (-0.67 years
  per SD).

Refitting the clocks with five other training seeds
([results/clock_seed_check.md](results/clock_seed_check.md)) keeps the picture: the fibrosis
column stays at 1.35 to 1.41 and 1.39 to 1.44 for
the two short-list chronological clocks, 0.20 to 0.36 and
0.23 to 0.36 for the two whole-panel ones, and
1.24 to 2.17 and 1.16 to 2.15 for the two
mortality clocks, whose stepwise step picks either one or two of the shared proteins.

Where each recipe departs from its original:

| simulated clock | original, as described in its own paper | not imitated here |
|---|---|---|
| prot_sparse_chrono | ProtAge [2]: gradient-boosted trees on 204 proteins selected from 2,897 | the model class and the selection method |
| prot_dense_chrono | the conventional chronological model of [3], called OrganAge_chrono in [1]: an elastic net trained on the whole panel | the penalty; here the weakest fifth of the features is dropped |
| prot_sparse_mortality | the conventional mortality model of [3], called OrganAge_mortality in [1]: a Cox elastic net trained on the whole panel | survival modelling; here a linear fit to a made-up risk score on 12 proteins chosen stepwise |
| prot_age_mortality | PAC [4]: chronological age plus 128 proteins, a Cox step and then a Gompertz model | survival modelling |
| prot_dense_chrono_b | ipfP3GPT [5]: a neural network on the whole panel with fibrosis-related pathway branches, trained on UK Biobank data | the network and its pathway design; this row is a second whole-panel fit and behaves like prot_dense_chrono |
| prot_organ_chrono | PAOPAC [6]: organ proxy clocks built from organ-enriched marker panels | the organ proxy structure; here one clock on 16 organ-panel proteins. [1] does not say which PAOPAC model it ran |

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
| antifibrotic | -0.1 | **-1.1** | -0.3 | **-2.1** | **-1.5** | -0.4 | **-1.1** | -0.1 | -0.1 |
| anti_inflammatory | +0.0 | -0.1 | -0.0 | **-1.4** | **-1.4** | -0.0 | -0.0 | +0.0 | +0.0 |
| senolytic_like | -1.4 | -1.1 | -1.1 | **-1.9** | **-2.0** | -1.1 | -1.1 | -1.1 | -1.5 |
| mtor_like | -1.2 | -0.9 | -0.9 | -1.1 | -1.1 | -0.9 | -0.9 | **-0.6** | -1.3 |
| reprogramming_like | -0.8 | -0.6 | -0.6 | -0.7 | -0.8 | -0.6 | -0.6 | **-5.3** | **-7.5** |
| immune_mobilizer | +0.0 | +0.0 | +0.0 | +0.0 | -0.0 | +0.0 | +0.0 | **-1.3** | +0.3 |
| restriction_like | -1.6 | -1.3 | -1.3 | -2.0 | -2.0 | -1.3 | -1.3 | -1.2 | -1.8 |

- **A compound that treats the disease moves every proteomic clock.** The antifibrotic
  archetype takes 0.1 years off mean organ age (one organ, the lung). The six
  proteomic clocks report 0.3 to 2.1 years younger. The two
  methylation clocks report 0.1 and 0.1 years younger. In the healthy cohort the same archetype has
  nothing to act on and no clock moves.
- **Mortality clocks read lower inflammation as younger.** The anti-inflammatory archetype
  changes no organ. Both proteomic mortality clocks report about 1.4 years younger.
  The chronological clocks stay near zero.
- **Methylation clocks can be moved directly.** The reprogramming-like archetype takes
  0.8 years off organ age and 5.3 to 7.5 years off
  the two methylation clocks. The proteomic clocks stay near the truth.
- **A cell-mix shift moves the chronological methylation clock** by 1.3 years with no
  organ change.
- The three archetypes coded to make every organ younger (senolytic-like, mTOR-like,
  restriction-like) move all eight clocks in the same direction. Which archetypes "work" is a
  coding choice. It is not evidence about senolytics, mTOR inhibitors or dietary restriction.

These patterns were coded into the simulator or follow from fitting linear clocks to it. The
table shows what this simulator's clocks read under each coded mechanism. It is not evidence
about any real clock, drug or trial, and it must not be used to read the result in [1] in
either direction. The antifibrotic archetype is not a model of rentosertib: its small effect on
organ age is a number chosen for this simulator.

## Environment QC (1000 seeds)

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

### Where each policy goes wrong: mean absolute error in years, by hidden archetype

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

### Reward against enrolment (reference analysis, only the arm size changed)

| people per arm | mean reward | right call | median error (yr) | gap to reference (SE) |
|---|---|---|---|---|
| 12 | 0.839 | 89% | 0.12 | +0.021 (0.005) |
| 20 | 0.854 | 92% | 0.11 | +0.005 (0.004) |
| 30 | 0.860 | 93% | 0.09 | +0.000 (0.000) |
| 60 | 0.846 | 94% | 0.08 | +0.014 (0.003) |
| 100 | 0.817 | 94% | 0.07 | +0.043 (0.004) |
| 150 | 0.782 | 95% | 0.06 | +0.077 (0.004) |

### Where the reference itself gets the call wrong (cells under 90 percent)

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

What the card says:

- The reference analysis lands within 0.09 years on the median and makes the
  right call 93 percent of the time on these seeds. It is a first draft and
  a floor, not an optimum.
- The costliest choices are reporting the best-looking clock (0.39
  reward lost), running each arm's follow-up samples on its own plate (0.29),
  having no placebo arm (0.27) and stopping at 4 weeks
  (0.21).
- **Trusting the six proteomic clocks because they agree** loses 0.04
  overall and is wrong exactly where it matters. On the antifibrotic archetype its error is
  0.49 years against 0.06 for the
  reference. The six agree there because they share inputs and a training population, not
  because six independent witnesses saw aging slow.
- Methylation alone is worse (0.11 lost): it over-reads the
  reprogramming-like archetype by 4.98 years. Averaging
  all eight clocks is still off by 1.17 years there.
- Punished, but only mildly: leaving the plate out of the analysis (gap +0.035, SE 0.005);
  enrolling 12 per arm instead of 30 (gap +0.021, SE 0.005).
- **Blind spots, reported and not hidden.** The reward cannot tell the reference from using the
  whole-panel chronological proteomic clock alone (gap -0.001, SE 0.005). In this simulator that
  clock is the one least sensitive to everything that is not aging, so using it alone costs
  nothing. A harder version needs a mechanism that fools it.
- The reference has one weak cell: the mTOR-like archetype at dose level 3, where it makes the
  right call 45 percent of the time (33 episodes). A cell-mix shift pushes the chronological
  methylation clock the other way there, the methylation median shrinks toward zero, and the
  conservative rule reports too little. The covariates would reveal the shift, and the reference
  does not use them.
- The reference errs on the side of missing real effects: 70 of its 74 wrong calls are real
  effects called not geroprotective, and in 61 of the 74 the true effect is within 0.3 years of
  the half-year threshold. The clocks under-read real change by about a fifth and the rule is
  conservative on top of that.
- The reward has a high floor. Answering "no effect" without looking scores
  0.60, because by design about half of the hidden compounds do nothing. Read
  every reward above against that floor.
- The cost term is steep. Under the reference analysis the reward peaks near 30 people per arm,
  and 150 per arm (0.78) scores lower than 12 per arm (0.84) although
  it makes the right call more often (95 against 89 percent).
  That is a property of one assumed cost constant, not a statement about trial economics.

## Can a policy that memorises beat the reference?

Trained on seeds 20000 to 22399. Each cell: mean reward, then the paired difference to the reference on the same seeds (standard error). Positive = beats the reference.

| policy | trial design | seeds 0 to 399 | seeds 1000 to 1399 |
|---|---|---|---|
| reference | reference design | 0.871 | 0.860 |
| memoriser | same design as the reference | 0.855, -0.016 (0.010) | 0.859, -0.001 (0.012) |
| classify_regress | same design as the reference | 0.889, +0.018 (0.009) | 0.888, +0.028 (0.011) |
| memoriser | 12 per arm | 0.839, -0.032 (0.012) | 0.849, -0.011 (0.014) |
| classify_regress | 12 per arm | 0.862, -0.010 (0.012) | 0.861, +0.001 (0.013) |
| memoriser | no placebo arm | 0.795, -0.077 (0.014) | 0.769, -0.091 (0.017) |
| classify_regress | no placebo arm | 0.794, -0.077 (0.014) | 0.771, -0.089 (0.017) |
| memoriser | stop at 4 weeks | 0.819, -0.053 (0.012) | 0.799, -0.061 (0.016) |
| classify_regress | stop at 4 weeks | 0.826, -0.045 (0.011) | 0.805, -0.055 (0.016) |
| memoriser | plates by arm | 0.724, -0.148 (0.017) | 0.732, -0.129 (0.018) |
| classify_regress | plates by arm | 0.727, -0.144 (0.017) | 0.731, -0.129 (0.018) |

Two learned policies, trained on 2,400 episodes with only what an agent legitimately gets
([shortcut.py](src/longevitygym/shortcut.py)):

- **Pure memorising does not win.** Recognising the archetype and answering with a memorised
  effect scores 0.855 and
  0.859 on two blocks of seeds, against
  0.871 and 0.860
  for the reference. The hidden potency is what prevents it.
- **Learning does help, which is the point.** Recognising the archetype and then estimating
  inside it beats the reference by 0.018
  and 0.028.
- **The design lessons still hold for the learner.** Take away the placebo arm, stop at 4
  weeks or put each arm on its own plate, and the same learner falls below the reference
  (-0.077, -0.045
  and -0.144 on the first block).

Seeds are public. Treat seeds 0 to 999 as a development set and score a trained agent on seeds
drawn at evaluation time.

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
longevity-gym qc --out results            # the QC card, about 5 minutes
longevity-gym shortcut --out results      # the memorising check, about 5 minutes
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
last digit.

## Limits

- "Biological age = mean organ age" is a definition made for this simulator. The field has no
  agreed ground truth, which is the reason to simulate one.
- Effect sizes are placeholders chosen so that each failure mode is visible. They are not
  estimates for any real drug, diet or procedure, and nothing here says any intervention works.
- The clocks are linear fits to simulated features. They imitate training recipes, not models.
  No published weight, protein list or dataset is used.
- The reference analysis leans on one assumption: that blood methylation does not see lung
  fibrosis at all. If it did, checking one modality against the other would protect less.
  Nothing here tests that assumption, and [1] had no second modality to check against.
- The reference analysis and the list of mistakes are a first draft. No one outside has
  reviewed them, and a learned policy already beats the reference.
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
