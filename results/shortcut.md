# Shortcut check: learned policies against the reference

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
