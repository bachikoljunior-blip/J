# rev97 — scalable anchorless global invariants

Root remains **NOT_AGI**.

For `...b3b`, full isomorphism enumeration on typical large instances was replaced with exact global isomorphism invariants. Each vertex receives an attribute-aware shortest-path distance distribution, degree, and neighbor-degree multiset. Candidate pairs must have identical signatures. A single exact adjacency-consistent witness is then found inside these invariant cells. Only singleton invariant cells are released, and only after a complete exact witness exists; search cutoff releases nothing.

Focused regression: **4 passed**. Across 35 random six-node cases every released pair is a subset of the independent exhaustive forced set. A 120-node un-attributed random graph maps under permutation with at least 100 singleton forced pairs and below search/runtime guards. An 80-cycle finds a witness but correctly releases no identity. `C6` versus two disjoint triangles is rejected by distance invariants despite identical degrees.

This solves the typical-large scalable child `...b3b` at `solved_v0_1`; it is not a worst-case polynomial graph-isomorphism claim. The next unresolved sibling is `...b3c`: anchorless partial/positive-edit-budget symmetry reasoning.