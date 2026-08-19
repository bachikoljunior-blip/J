# rev96 — anchorless global symmetry reasoning, bounded exact case

Root remains **NOT_AGI**.

The anchorless duplicate-attribute leaf was attacked directly by removing the assumption that any pair is pre-anchored. The implementation performs a globally consistent backtracking enumeration of all exact attributed graph isomorphisms, with attribute, degree, and mapped-adjacency pruning. A correspondence is released only if it appears in the intersection of every exact isomorphism. If the search budget is reached, it fails closed and releases nothing.

Focused regression: **4 passed**. A permuted five-node path releases only its globally fixed center; a six-cycle releases no pair across 12 symmetries; 40 random permuted six-node attributed graphs match an independent full-permutation oracle exactly; and an intentionally tiny search budget releases nothing.

The broad anchorless leaf remains unresolved because enumeration is factorial in the worst case and only covers zero-edit full isomorphism. It is decomposed into `...b3a` bounded exact enumeration (`solved_v0_1`), `...b3b` scalable anchorless symmetry reasoning (unresolved), and `...b3c` partial/positive-edit-budget symmetry reasoning (unresolved). Estimated active-node count: **478**, below prediction 512.