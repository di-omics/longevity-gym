# Shortcut check: learned policies against the reference

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
