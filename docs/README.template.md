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
  everything else is held fixed.

What the simulated clocks read:

- All of them follow organ aging, at <<d:slope_min>> to <<d:slope_max>> years per year. The
  chronological clocks under-read a real change by about a fifth.
- The two proteomic mortality clocks read one SD of inflammation as about <<d:infl_mort>> years.
  The chronological clocks do not (<<d:infl_chrono_max>> at most).
- **All six proteomic clocks read fibrosis activity as age**, from <<d:fib_min>> to
  <<d:fib_max>> years per unit, because each of them uses at least one of the four shared
  proteins. This is built in. The two methylation clocks read none of it, which is also built
  in: in this simulator blood methylation does not see the lung.
- The chronological methylation clock reads the blood cell mix (<<clock:epi_chrono:mix>> years
  per SD).

Refitting the clocks with five other training seeds
([results/clock_seed_check.md](results/clock_seed_check.md)) keeps the picture: the fibrosis
column stays at <<seed:prot_sparse_chrono:fibrosis>> and <<seed:prot_organ_chrono:fibrosis>> for
the two short-list chronological clocks, <<seed:prot_dense_chrono:fibrosis>> and
<<seed:prot_dense_chrono_b:fibrosis>> for the two whole-panel ones, and
<<seed:prot_sparse_mortality:fibrosis>> and <<seed:prot_age_mortality:fibrosis>> for the two
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

<<TABLE:readouts>>

- **A compound that treats the disease moves every proteomic clock.** The antifibrotic
  archetype takes <<d:antifib_truth>> years off mean organ age (one organ, the lung). The six
  proteomic clocks report <<d:antifib_prot_lo>> to <<d:antifib_prot_hi>> years younger. The two
  methylation clocks report <<d:antifib_epi>>. In the healthy cohort the same archetype has
  nothing to act on and no clock moves.
- **Mortality clocks read lower inflammation as younger.** The anti-inflammatory archetype
  changes no organ. Both proteomic mortality clocks report about <<d:inflam_mort>> years younger.
  The chronological clocks stay near zero.
- **Methylation clocks can be moved directly.** The reprogramming-like archetype takes
  <<d:reprog_truth>> years off organ age and <<d:reprog_epi_lo>> to <<d:reprog_epi_hi>> years off
  the two methylation clocks. The proteomic clocks stay near the truth.
- **A cell-mix shift moves the chronological methylation clock** by <<d:mix_epi>> years with no
  organ change.
- The three archetypes coded to make every organ younger (senolytic-like, mTOR-like,
  restriction-like) move all eight clocks in the same direction. Which archetypes "work" is a
  coding choice. It is not evidence about senolytics, mTOR inhibitors or dietary restriction.

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
  a floor, not an optimum.
- The costliest choices are reporting the best-looking clock (<<qc:cherry_pick_best_clock:gap>>
  reward lost), running each arm's follow-up samples on its own plate (<<qc:plates_by_arm:gap>>),
  having no placebo arm (<<qc:no_placebo:gap>>) and stopping at 4 weeks
  (<<qc:short_trial_4wk:gap>>).
- **Trusting the six proteomic clocks because they agree** loses <<qc:proteomics_only:gap>>
  overall and is wrong exactly where it matters. On the antifibrotic archetype its error is
  <<err:proteomics_only:antifibrotic>> years against <<err:reference:antifibrotic>> for the
  reference. The six agree there because they share inputs and a training population, not
  because six independent witnesses saw aging slow.
- Methylation alone is worse (<<qc:epigenetics_only:gap>> lost): it over-reads the
  reprogramming-like archetype by <<err:epigenetics_only:reprogramming_like>> years. Averaging
  all eight clocks is still off by <<err:average_all_clocks:reprogramming_like>> years there.
<<d:mild_bullet>>
<<d:blind_bullet>>
<<d:weak_cells_bullet>>
- The reward has a high floor. Answering "no effect" without looking scores
  <<qc:always_no:mean>>, because by design about half of the hidden compounds do nothing. Read
  every reward above against that floor.
- The cost term is steep. Under the reference analysis the reward peaks near 30 people per arm,
  and 150 per arm (<<enrol:150:mean>>) scores lower than 12 per arm (<<enrol:12:mean>>) although
  it makes the right call more often (<<enrol:150:call>> against <<enrol:12:call>> percent).
  That is a property of one assumed cost constant, not a statement about trial economics.

## Can a policy that memorises beat the reference?

<<TABLE:shortcut>>

Two learned policies, trained on 2,400 episodes with only what an agent legitimately gets
([shortcut.py](src/longevitygym/shortcut.py)):

- **Pure memorising does not win.** Recognising the archetype and answering with a memorised
  effect scores <<short:memoriser:same design as the reference:0:mean>> and
  <<short:memoriser:same design as the reference:1:mean>> on two blocks of seeds, against
  <<short:reference:reference design:0:mean>> and <<short:reference:reference design:1:mean>>
  for the reference. The hidden potency is what prevents it.
- **Learning does help, which is the point.** Recognising the archetype and then estimating
  inside it beats the reference by <<short:classify_regress:same design as the reference:0:gap>>
  and <<short:classify_regress:same design as the reference:1:gap>>.
- **The design lessons still hold for the learner.** Take away the placebo arm, stop at 4
  weeks or put each arm on its own plate, and the same learner falls below the reference
  (<<short:classify_regress:no placebo arm:0:gap>>, <<short:classify_regress:stop at 4 weeks:0:gap>>
  and <<short:classify_regress:plates by arm:0:gap>> on the first block).

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
