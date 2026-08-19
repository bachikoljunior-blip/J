# rev94 — third-order motif lower bound for partial alignment

Root remains **NOT_AGI**.

Target leaf `...cbb` asked for a higher-order structural lower bound that can stay informative when selected-degree intervals overlap. I added a triangle-count invariant for partial graph matching.

For any fixed common size `s`, if two selected induced subgraphs disagree on `E` edges under a bijection, changing those `E` edges changes triangle count by at most `E*(s-2)`. Therefore `E >= ceil(|ΔT|/(s-2))`. With insertions/deletions the selected vertex sets are unknown, so the implementation computes a safe interval for the triangle count of every possible `s`-vertex induced subgraph. The lower endpoint subtracts an over-approximation of triangles removable by omitted vertices; the upper endpoint is bounded by both the full-graph triangle count and `C(s,3)`. The final lower bound is the minimum over every attribute-feasible common size, so selecting more than the minimum cannot invalidate the certificate.

Validation: C6 versus two disjoint triangles is a deliberately degree-regular adversary; with enough omissions the coarse motif signal correctly falls to zero; every exact subset triangle count of random graphs up to six vertices lies inside the interval; and 160 random partial graph pairs (3–5 vertices per side) were exhaustively enumerated over subsets and bijections without a lower-bound violation. Focused regression: **4 passed**.

This solves `...cbb` at `solved_v0_1`. The next existing leaf is `...cbc`: validate and scale the combined lower-bound family on larger multi-bucket partial alignments and adversarial symmetry. AGI remains un-certified.