# results/

Every file here is written by one `longevity-gym` subcommand run with `--out results`. Nothing
in this folder is edited by hand, and [README.md](../README.md) is rebuilt from it by
[tools/build_readme.py](../tools/build_readme.py). A test fails if the two disagree.

Three file names differ from the subcommand that writes them: `seedcheck` writes
`clock_seed_check`, `qc` writes `qc_clock_trial`, and `realcheck` writes `real_check`.

| file | written by | rough run time | README section that quotes it |
|---|---|---|---|
| [clocks.md](clocks.md) | `longevity-gym clocks --out results` | seconds | The eight simulated clocks |
| [clock_seed_check.md](clock_seed_check.md) | `longevity-gym seedcheck --out results` | seconds | The eight simulated clocks |
| [readouts.md](readouts.md) | `longevity-gym readouts --out results` | seconds | What each simulated clock says, next to the simulated truth |
| [qc_clock_trial.md](qc_clock_trial.md), [.json](qc_clock_trial.json) | `longevity-gym qc --out results` | several minutes | Environment QC |
| [shortcut.md](shortcut.md), [.json](shortcut.json) | `longevity-gym shortcut --out results` | several minutes | Can a policy that memorises beat the reference? |
| [real_check.md](real_check.md), [.json](real_check.json) | `longevity-gym realcheck --out results` | under a minute | How far is the simulator from real clock readouts? |
| [qc_clock_trial_calibrated.md](qc_clock_trial_calibrated.md), [.json](qc_clock_trial_calibrated.json) | `longevity-gym qc --noise calibrated --out results` | several minutes | How far is the simulator from real clock readouts? |

The `.json` twin of a table holds the same result in full, and the README builder reads the
`.json` where one exists. `qc` uses 2,000 seeds unless `--seeds` says otherwise, and the two QC
cards must be run with the same number of seeds.

Run times are for one laptop and are only a guide. Other builds of Python and numpy can differ
in the last digit, so regenerate every file on the same machine before rebuilding the README.
