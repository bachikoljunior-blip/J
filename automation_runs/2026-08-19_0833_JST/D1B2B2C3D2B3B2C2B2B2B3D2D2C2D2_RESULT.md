# rev80 result — finite-family RFF approximation certificate

Status: **solved_v0_1 for this scoped child**. Root remains **NOT_AGI**.

For every atomic attribute pair, the m random-Fourier summands lie in [-2,2], so Hoeffding gives `P(|k_hat-k| >= eps) <= 2 exp(-m eps^2/8)`. For a declared finite family containing M matched atomic comparisons in total, assigning failure probability `delta/M` to each pair and applying the union bound yields the simultaneous atomic radius

`eps_M = sqrt(8 log(2M/delta)/m)`.

For a graph pair with `P` matched node pairs across all structural refinement colors/depths and node-mass normalization `1/sqrt(n_a n_b)`, the unnormalized structural graph-kernel error is therefore bounded by

`eps_M * P / sqrt(n_a n_b)`

on the simultaneous event. Dependence among graph-pair estimates does not invalidate this union bound because only the per-atomic Hoeffding events require the iid feature draws.

The implementation counts the actual finite-family multiplicity instead of silently reusing a pointwise confidence level. Dedicated tests verify the multiple-comparison penalty grows with family size, zero-overlap cases have zero error, permutation invariance is preserved, and independent shifted synthetic graph pairs satisfy their realized bounds in the regression sample. Cumulative local regression rev75–80: **30 passed**.

This certificate is finite-family and pointwise-in-the-declared-family. It does not certify adaptive post-selection of arbitrary future graph pairs or population calibration under unknown shift; those remain separate leaves.
