# rev97 — scalable cycle symmetry/orbit certificate

Root remains **NOT_AGI**.

The remaining scalable-symmetry child is decomposed by explicit graph-family structure rather than falling back to unbounded search.

rev97 implements a complete polynomial-time orbit certificate for connected single cycles. After validating that each graph is one degree-2 connected cycle, it fixes one source traversal and enumerates every target start vertex and both target orientations. This is exactly the dihedral isomorphism family (at most `2n` mappings); exact attributes filter the family. The forced-pair set is the exact intersection across all valid mappings.

No arbitrary symmetry choice is released. Uniform cycles therefore certify `no forced pairs`, while a sufficiently distinguishing attribute pattern can reduce the family to one exact mapping. The implementation checks cycle structure, attribute equality along every proposed mapping, and mapped cycle edges.

Repository regression includes a 500-node uniform cycle, for which the certificate expects all 1,000 dihedral mappings and an empty forced-pair set, demonstrating a symmetry case that is large but does not require exponential backtracking.

The scalable-symmetry parent `...c2d3b2b2b3c3` remains unresolved and is decomposed into:

- `...c2d3b2b2b3c3a`: scalable exact orbit intersection for single cycles via complete dihedral enumeration — `solved_v0_1`;
- `...c2d3b2b2b3c3b`: scalable twin/module quotient automorphism generators — unresolved;
- `...c2d3b2b2b3c3c`: general scalable automorphism/orbit handling beyond recognized structural families — unresolved.

Estimated active-node count after decomposition: **478**, below prediction **512**.
