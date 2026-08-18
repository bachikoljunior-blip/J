# rev75 attempt — scale attributed-graph invariant kernels beyond factorial orbit averaging

Root certification remains **NOT_AGI**.

## Direct attempt

Implemented a polynomial-time explicit attributed-graph feature map combining deterministic 1-WL structural refinement with random-Fourier features of continuous node attributes. Continuous features are summed within structural color classes at every refinement depth, yielding a node-permutation-invariant sparse feature map. Kernel evaluation is an inner product of these explicit features, optionally with per-graph normalization, so its Gram matrix is PSD by construction.

The implementation does **not** enumerate graph automorphisms or node permutations. A 650-node sparse attributed graph is covered by the focused regression.

## Empirical checks

Local focused test result: **5 passed**.

- exact invariance under a random relabeling of a 90-node attributed graph;
- successful feature construction on a 650-node graph without factorial enumeration;
- continuous attribute changes reduce similarity on a fixed skeleton;
- normalized Gram matrix is symmetric PSD up to numerical tolerance;
- a path/cycle structural change is separated in the bounded example.

## Why the parent remains unresolved

This is a scalable invariant surrogate, not a complete invariant. Standard 1-WL has known collision classes, finite digests can in principle collide, and finite random-Fourier features approximate rather than exactly equal the underlying RBF attribute kernel. Therefore this result cannot replace the exact small-graph orbit average for all graphs.

## Decomposition

The leaf `D1b2b2c3d2b3b2c2b2b2b3d2d2c2` is decomposed into:

- `...c2a`: polynomial-time PSD permutation-invariant attributed-graph surrogate — **solved_v0_1** in the tested scope;
- `...c2b`: detect/certify important collision classes of the scalable surrogate and fail closed when distinction is required — unresolved;
- `...c2c`: combine scalable screening with exact/parameterized refinement so hard cases can be escalated without factorial work on easy cases — unresolved;
- `...c2d`: establish approximation/stability bounds for continuous attributes and validate under independent distribution shift — unresolved.

Estimated active-node count after this decomposition: **443**, below the current prediction **512**; prediction-exceeded whole-tree consolidation is not triggered.
