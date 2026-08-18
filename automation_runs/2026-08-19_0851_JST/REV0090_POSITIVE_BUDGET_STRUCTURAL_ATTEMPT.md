# rev90 direct attempt — structural forcing with a positive edge-disagreement budget

Root remains **NOT_AGI**.

Implemented a conservative candidate-superset certificate for positive common-edge-disagreement budgets. Exact-attribute capacity still supplies the initial forced anchors. For each remaining same-attribute candidate pair, the routine computes the number of adjacency disagreements to those already forced anchors; candidates whose anchor mismatches alone exceed the full budget are removed. A Hopcroft–Karp maximum matching is then computed on this **superset** of every feasible remaining assignment. When the maximum size exactly equals the required remaining cardinality, a matched edge is considered structurally forced only if deleting that edge reduces the superset maximum below the required cardinality. Because the proof works in a superset, any such edge is necessary for every truly feasible alignment. A full candidate witness is then directly checked against the total declared edge-disagreement budget before any identities are released.

Focused local regression: **3 passed**. Duplicate-attribute nodes with anchor-adjacency codes separated by more than the allowed error are recovered; one actual common-edge disagreement is tolerated and counted; a symmetric cycle releases no pairs. A separate local oracle audit over **400 random small positive-budget cases** found no released pair outside the independent exhaustive forced set.

The broad child remains unresolved and is decomposed into:

- `...c2d3b2b2b2a`: bounded essential-edge forcing in an anchor-mismatch compatibility superset, plus direct witness verification — `solved_v0_1`;
- `...c2d3b2b2b2b`: scalable essential-edge detection without per-matched-edge recomputation — unresolved;
- `...c2d3b2b2b2c`: incorporate the **total** remaining disagreement budget into assignment lower bounds rather than only per-pair anchor screening — unresolved.

Estimated active-node count after decomposition: **469**, below prediction 512.
