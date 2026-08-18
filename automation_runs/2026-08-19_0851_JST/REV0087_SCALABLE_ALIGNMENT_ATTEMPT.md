# rev87 direct attempt — scalable large-graph alignment with ambiguity certificates

Root remains **NOT_AGI**.

A fail-closed scalable fast path was implemented for the full, exact attributed-isomorphism case. It performs joint 1-Weisfeiler-Lehman color refinement across both graphs, releases a mapping only when every final color class is singleton, and then directly verifies the induced bijection against the complete adjacency and attribute arrays. If a non-singleton color class remains, it returns no pairs rather than arbitrarily breaking symmetry. If the refined color inventories differ or the induced singleton mapping fails direct verification, it rejects exact full alignment.

Focused local regression: **4 passed**. A 220-node random graph with constant attributes was correctly aligned after permutation; a symmetric 20-cycle abstained; a path-versus-cycle mismatch was rejected; and a distinct-attribute permutation passed direct verification.

This does not solve the general scalable partial-edit leaf. The parent is decomposed into:

- `...c2d3b2b1`: scalable full exact-isomorphism WL singleton certificate with direct verification — `solved_v0_1` for this bounded semantic class;
- `...c2d3b2b2`: scalable partial-edit forced-pair certificates that remain sound with insertions/deletions — unresolved;
- `...c2d3b2b3`: scalable handling of hard symmetric/non-WL-distinguishable cases without fabricating identity — unresolved.

The separate noise-tolerant attribute leaf `...c2d3b2c` remains unresolved. Estimated active-node count after this decomposition: **460**, below prediction 512.
