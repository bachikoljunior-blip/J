# rev113 — adversarial independent-oracle audit

Root remains **NOT_AGI**.

The final rev111 child mixed two materially different obligations: adversarial correctness evidence for the exact implementation, and the still-missing general worst-case quasipolynomial ceiling. It is therefore decomposed into (a) independent-oracle/adversarial validation and (b) worst-case general-path complexity. This revision solves (a); (b) remains open.

## Complete Graph Atlas audit

Using NetworkX 3.6.1 as an independent implementation oracle, every nonempty graph in `networkx.graph_atlas_g()` was checked: **1,252 graphs, all simple unlabeled graphs through 7 vertices represented by the atlas**.

For each graph:

- `exact_gi_isomorphism_coset(G,G)` returned an exact automorphism coset;
- its stabilizer-chain automorphism order exactly matched the number of automorphisms independently enumerated by `networkx.algorithms.isomorphism.GraphMatcher(G,G).isomorphisms_iter()`;
- `exact_group_pruned_canonical_label` completed;
- after a fixed nontrivial vertex relabeling, the canonical byte code was unchanged.

Maximum observed exact-GI/group reconstruction search nodes across the atlas: **126**. Maximum observed canonical-search states: **9**.

## Hard symmetry families

Independent known group orders were checked without enumerating those groups in the AGI-GI implementation:

- complete bipartite K4,4: order 1,152; K6,6: 1,036,800; K8,8: **3,251,404,800**;
- hypercubes Q3/Q4/Q5: orders 48 / 384 / 3,840;
- Petersen graph: order 120;
- rook graphs R3/R4: orders 72 / 1,152;
- triangular graphs T6/T7/T8 (line graphs of K6/K7/K8): orders 720 / 5,040 / 40,320.

Canonical labeling also completed on Q5 (32 vertices), K8,8 (16 vertices), and T8 (28 vertices), each with one verified canonical leaf after exact orbit pruning.

## Strongly-regular adversarial pair

The Shrikhande graph and the 4×4 rook graph have the same strongly-regular parameters and defeat plain degree/1-WL separation. An independently constructed Shrikhande Cayley graph and the rook graph were checked with NetworkX:

- NetworkX: non-isomorphic;
- AGI-GI exact GI coset: `non_isomorphic` after 113 search nodes;
- NetworkX automorphism enumeration: Shrikhande 192, rook 1,152;
- AGI-GI reconstructed orders: exactly 192 and 1,152;
- canonical codes: distinct, as required.

This is strong correctness/adversarial evidence for the current exact implementation. It does **not** establish the remaining worst-case quasipolynomial bound for arbitrary graph families.