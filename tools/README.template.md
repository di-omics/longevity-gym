<!-- README.md is generated from tools/README.template.md by tools/build_readme.py. Edit the template, then rebuild. -->
# Longevity RL

Two simulated decision tasks for longevity research. Select candidates against two
endpoints on a fixed assay budget. Then, in a separate clock-trial benchmark, infer
whether a change in aging-clock readings reflects a change in simulated organ age.

**Status: v0.1, simulation only.** Nothing here is trained on real data. The repo holds no real
proteomic or methylation data, no published clock, no participant-level trial data and no
stored model or agent. The clocks, shortcut-check policies and benchmark outcome model
are fitted at run time on simulated data. The only real numbers are a few aggregate
statistics computed from the open supplementary tables of [1]. They are used in one section,
to check the simulator's noise and to set one optional noise profile. Every other number is an
assumed default ([docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md)). Sister repo to
[drugdev-gym](https://github.com/di-omics/drugdev-gym): hidden truth, named mistakes, and a QC
card that says what the reward can and cannot see.

## Few-shot batch selection

Can two-round lookahead find more candidates that meet two criteria on the same
experimental budget? `longevity-rl replay` starts five policies with the same
eight observations. Each selects 24 new candidates in each of four rounds. A hit
passes both simulated endpoints, which stand in for potency and stability.

The pool holds 1,536 anonymous items in eight groups. A separate capacity calculation
allows 336 paired observations per batch under the assumption of two 1,536-well
plates, one per endpoint, with 192 control wells and four wells per item per plate.
The planner simulates possible observations before choosing a batch. It and the
adaptive baselines update a group-level prior that matches the simulator. Each
campaign starts fresh. This benchmark covers decisions in a toy environment, with
no molecular sequences, wet-lab measurements or training across peptide families.

```sh
longevity-rl replay --seed 17
longevity-rl replay --seed 0 --campaigns 100
```

The first command shows cumulative hits by round for random selection, a fixed
ranking, an updated greedy ranking, batch Thompson sampling, and the planner.
The second reports paired results across seeds. Add `--json` to either command.

<<d:replay_results>>

## Aging-clock benchmark

`longevity-rl benchmark` compares ways to interpret the same simulated trial. Every
policy gets the same placebo-controlled trial and clock panel. The model-based policy
compares the two clock-family medians with those from up to eight similar training
trials and chooses the report with the highest expected reward under those outcomes.
The scripted reference, the all-clock average and the constant negative call get the
same evidence. On separate test seeds the benchmark reports reward, error in years
and accuracy in detecting the simulator's geroprotective effect. Each decision is
a single final report about a simulated trial with a fixed design.

```sh
longevity-rl benchmark --train-seeds 32 --test-seeds 16 --seed 0
longevity-rl benchmark --noise calibrated --json
```

<<d:benchmark_results>>

## Where things are

| I want to | Look here |
|---|---|
| compare batch-selection policies on the same synthetic pool | `longevity-rl replay --seed 17`, [replay.py](src/longevityrl/replay.py), [results/replay.json](results/replay.json) |
| compare ways to interpret the same simulated clock trial | `longevity-rl benchmark`, [benchmark.py](src/longevityrl/benchmark.py), [results/benchmark.json](results/benchmark.json) |
| see the task as an agent sees it, or run one episode | `longevity-rl spec`, `longevity-rl play --seed 3`, [env.py](src/longevityrl/env.py) |
| read how the simulated people and their omics are made | [biology.py](src/longevityrl/biology.py) |
| read how the clocks are fitted and what each one reads | [clocks.py](src/longevityrl/clocks.py), [results/clocks.md](results/clocks.md), [results/clock_seed_check.md](results/clock_seed_check.md) |
| see what each archetype does to each clock, next to the truth | [interventions.py](src/longevityrl/interventions.py), [readouts.py](src/longevityrl/readouts.py), [results/readouts.md](results/readouts.md) |
| read the scripted reference analysis and the named mistakes | [policies.py](src/longevityrl/policies.py) |
| read the QC card | [envqc.py](src/longevityrl/envqc.py), [results/qc_clock_trial.md](results/qc_clock_trial.md) |
| check whether a memorising policy beats the reference | [shortcut.py](src/longevityrl/shortcut.py), [results/shortcut.md](results/shortcut.md) |
| compare the simulator's noise with real clock readouts | [realcheck.py](src/longevityrl/realcheck.py), [tools/real_targets.py](tools/real_targets.py), [results/real_check.md](results/real_check.md) |
| find an assumed number and the module that holds it | [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) |
| find the command that writes each results file | [results/README.md](results/README.md) |
| change this README | [tools/README.template.md](tools/README.template.md), then [tools/build_readme.py](tools/build_readme.py) |
| read or run the tests | `pytest -q`; [tests/](tests) has one file each for benchmark, clocks, env, interventions, policies, realcheck and replay, plus test_repo.py for the repo's own rules |

This README is generated from [tools/README.template.md](tools/README.template.md). Edit the
template, not README.md.

## Run it

Needs Python 3.11 or newer. Until 19 November 2026 this repo was named longevity-gym: the command
is now `longevity-rl` and the Python import is `longevityrl`.

```bash
pip install -e ".[dev]"
pytest -q
longevity-rl spec                         # the task as an agent sees it
longevity-rl play --seed 3                # one episode with the scripted reference
longevity-rl clocks                       # the clock table (add --out results to save it)
longevity-rl seedcheck                    # the same after refitting with other seeds
longevity-rl readouts                     # clocks vs truth
longevity-rl qc --out results             # the QC card, several minutes
longevity-rl shortcut --out results       # the memorising check, several minutes
longevity-rl realcheck --out results      # simulator noise against real clock readouts
longevity-rl qc --noise calibrated --out results    # the QC card under real-world noise
python -m longevityrl spec                # the same CLI without the console script
python tools/build_readme.py              # rebuild this README from results/
```

```python
from longevityrl import make
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

1. **People** ([biology.py](src/longevityrl/biology.py)). Each simulated person has seven
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
3. **Clocks** ([clocks.py](src/longevityrl/clocks.py)). Eight ridge regressions fitted to
   simulated people. Six imitate the training recipes of the six clocks in [1] as far as a
   small linear model can. Two methylation clocks are this repo's addition; the study in [1]
   used proteomic clocks only. Each clock comes with a calibration card: how far its reading
   moves per year of true organ aging and per unit of two measurable covariates, in healthy
   people. How a clock reads disease is not on its card.
4. **Interventions** ([interventions.py](src/longevityrl/interventions.py)). Eight abstract
   archetypes at three dose levels, each with two hidden potency multipliers (0.25 to 1.75), so
   the true effect is a continuous number. Some are coded to change organ aging. Some only
   change what leaks into a clock. The agent sees a code name, never the mechanism.
5. **Environment** ([env.py](src/longevityrl/env.py)). `clock_trial`, two steps: design a
   trial (arm size, placebo, duration, plate layout, covariates, which clocks), receive
   per-sample clock readings, then report the effect in years at 26 weeks. The report also
   carries a yes or no on geroprotective (half a year or more younger), which must agree with
   the number. Reward = half for the estimate, half for the call, minus enrolment cost. One env
   object is one episode.
6. **Environment QC** ([envqc.py](src/longevityrl/envqc.py)). A scripted reference analysis,
   twelve named mistakes that each change one thing, and two constant-answer baselines, all run
   on the same seeds, people and noise.

## The eight simulated clocks

<<TABLE:clocks>>

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

- All of them follow organ aging, at <<d:slope_min>> to <<d:slope_max>> years per year. The
  chronological clocks under-read a real change by about a fifth.
- The two proteomic mortality clocks read one unit of inflammation as about <<d:infl_mort>>
  years. The chronological clocks and both methylation clocks do not (<<d:infl_other_max>> at
  most).
- **All six simulated proteomic clocks read fibrosis activity as age**, from <<d:fib_min>> to
  <<d:fib_max>> years per unit. Each uses at least one of the four shared proteins, and
  fibrosis also nudges the rest of the proteome in the "older" direction. This is built in. The
  two whole-panel
  clocks read it least: 4 percent of their simulated training population carried some fibrosis
  activity, and a whole-panel fit learns to discount part of it. Fitted on healthy people only,
  the same two clocks read fibrosis about twice as strongly (a test checks this).
- The two methylation clocks read no fibrosis at all, which is also built in: in this simulator
  blood methylation does not see fibrosis activity.
- The chronological methylation clock reads the blood cell mix (<<clock:epi_chrono:mix>> years
  per unit).

Refitting the clocks with five other training seeds gives the same picture
([results/clock_seed_check.md](results/clock_seed_check.md)). The fibrosis column ranges over
<<seed:prot_sparse_chrono:fibrosis>> and <<seed:prot_organ_chrono:fibrosis>> for the two
short-list chronological clocks, <<seed:prot_dense_chrono:fibrosis>> and
<<seed:prot_dense_chrono_b:fibrosis>> for the two whole-panel ones, and
<<seed:prot_sparse_mortality:fibrosis>> and <<seed:prot_age_mortality:fibrosis>> for the two
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

<<TABLE:readouts>>

- **In this simulator a compound that treats the disease moves every proteomic clock.** The
  antifibrotic archetype takes <<d:antifib_truth>> years off mean organ age (one organ, the
  lung). The six proteomic clocks report <<d:antifib_prot_lo>> to <<d:antifib_prot_hi>> years
  younger. The two methylation clocks report <<d:antifib_epi>>. In the healthy cohort the same
  archetype has nothing to act on and no clock moves.
- **The two proteomic mortality clocks read lower inflammation as younger.** The
  anti-inflammatory archetype changes no organ. Both report about <<d:inflam_mort>> years
  younger. The chronological clocks and both methylation clocks stay near zero.
- **The simulated methylation clocks can be moved directly.** The reprogramming-like archetype
  takes <<d:reprog_truth>> years off organ age and <<d:reprog_epi_lo>> to <<d:reprog_epi_hi>>
  years off the two methylation clocks. The proteomic clocks stay near the truth.
- **A cell-mix shift moves the simulated chronological methylation clock** by <<d:mix_epi>>
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

## Environment QC (<<d:n_seeds>> seeds)

<<TABLE:qc>>

What the card says:

- The reference analysis lands within <<qc:reference:err>> years on the median and makes the
  right call <<qc:reference:call>> percent of the time on these seeds. It is a first draft and
  a floor, not an optimum. Treat the second decimal of every figure on this card as noise: on
  another block of seeds the smallest gaps can change verdict.
<<d:costliest_bullet>>
- **Trusting the six proteomic clocks because they agree** loses <<qc:proteomics_only:gap>>
  overall, and in this simulator it is wrong where it matters. On the antifibrotic archetype
  its error is <<err:proteomics_only:antifibrotic>> years against
  <<err:reference:antifibrotic>> for the reference. The six simulated clocks agree there because
  they were built to share inputs and a training population. That is a property of this toy
  world. It is not a finding about the six real clocks or about the trial in [1].
- Methylation alone loses <<qc:epigenetics_only:gap>>: it over-reads the reprogramming-like
  archetype by <<err:epigenetics_only:reprogramming_like>> years. Averaging all eight clocks is
  still off by <<err:average_all_clocks:reprogramming_like>> years there.
<<d:one_clock_bullet>>
<<d:mild_bullet>>
<<d:blind_bullet>>
<<d:weak_cells_bullet>>
<<d:wrong_calls_bullet>>
- The reward has a high floor. Answering "no effect" without looking scores
  <<qc:always_no:mean>>, because <<d:zero_share>> percent of the hidden compounds do nothing.
  Read every reward above against that floor.
- The cost term is steep. Under the reference analysis the reward is highest at
  <<d:enrol_peak>> people per arm on this grid, and 150 per arm (<<enrol:150:mean>>) scores
  lower than 12 per arm (<<enrol:12:mean>>) although it makes the right call more often
  (<<enrol:150:call>> against <<enrol:12:call>> percent). That is a property of one assumed cost
  constant, not a statement about trial economics.

## Can a policy that memorises beat the reference?

<<TABLE:shortcut>>

Two learned policies, refitted on every run from 2,400 episodes with only what an agent
legitimately gets ([shortcut.py](src/longevityrl/shortcut.py)):

<<d:memoriser_bullet>>
<<d:learner_bullet>>
<<d:off_range_bullet>>
<<d:lessons_bullet>>

Seeds are public, and the task text alone (compound code, dose level, cohort) is enough to
identify most development seeds. Treat seeds 0 to <<d:last_seed>> as a development set, and
score a trained agent on seeds drawn at evaluation time from a range too large to enumerate.

## How far is the simulator from real clock readouts?

The supplementary tables of [1] are public (the article is open access, CC BY 4.0). They list
clock predictions for 168 samples with no participant, arm or visit label, and summary
statistics for every arm and visit. A few aggregates were computed from them with
[tools/real_targets.py](tools/real_targets.py). No participant-level data is in this repo, and
the samples were not linked back to participants. The full comparison is in
[results/real_check.md](results/real_check.md). It compares noise and agreement between clocks
only, and says nothing about any drug.

<<d:real_quiet_bullet>>
<<d:real_corr_bullet>>
<<d:real_card_bullet>>
<<d:real_card_verdicts_bullet>>
<<d:real_share_bullet>>

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
- One clock-trial environment, one disease cohort, two modalities. Next: transcriptomic and
  blood chemistry clocks, a layer that replays real public clock readouts, and an LLM-agent
  harness.

## Licence

MIT, see [LICENSE](LICENSE).

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
