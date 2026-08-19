# rev99 — scalable anchorless partial-budget branch-and-bound

Root remains **NOT_AGI**.

Added a fail-closed branch-and-bound solver for minimum-cardinality partial mappings with exact attributes and a positive common-edge disagreement budget. Search orders rare attribute/degree candidates first, maintains incremental edge-disagreement cost, prunes by remaining attribute capacity, and may omit source vertices when the unmatched budget permits it. After one feasible witness is found, each witness pair is excluded in a separate feasibility search; a pair is certified forced only when that exclusion search exhausts without a feasible alternative. Any cutoff or exclusion-check limit only reduces claims.

Focused regression: **4 passed**. Across 24 random five-node cases every released pair is a subset of the exhaustive exact forced set. A 28-vs-30 planted case with seven repeated attribute buckets, two unmatched distractors and three edge flips finds a full 28-pair witness; every released pair lies in the planted map. A symmetric cycle releases nothing, and a tiny cutoff fails closed.

This solves `...b3c2` at the current typical-instance level. Together with rev98, `...b3c` and then the anchorless duplicate-attribute parent `...b3` integrate as `solved_v0_1`.