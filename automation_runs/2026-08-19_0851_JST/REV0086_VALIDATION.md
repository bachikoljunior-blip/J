# rev86 — bounded exact consensus validation

Root remains **NOT_AGI**.

The rev85 bounded partial-alignment consensus routine was validated against an independently implemented brute-force oracle. The validator exhausts all 3-node undirected graph pairs, all binary single-attribute assignments, and seven unmatched/edge-disagreement budget combinations: **28,672 exact cases**. It also checks **500** asymmetric-size random cases up to 4x4 vertices.

Observed forced-pair sets, feasible-solution counts, and status values matched the oracle in every case. An additional local monotonicity audit over 300 random 4x4 cases confirmed that relaxing the edge-disagreement budget never reduced the feasible-solution count and never created a new forced pair when the tighter problem was feasible.

Local result: **PASS (28,672 exhaustive + 500 asymmetric random + 300 monotonicity cases)**.

Therefore leaf `D1b2b2c3d2b3b2c2b2b2b3d2d2c2d3b2a` is marked `solved_v0_1` for its bounded exact-attribute semantics. This does not validate scalability or noisy-attribute identity inference.
