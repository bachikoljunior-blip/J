# rev92 — total remaining disagreement budget as an assignment lower bound

Root remains **NOT_AGI**.

Direct attempt on `D1b2b2c3d2b3b2c2b2b2b3d2d2c2d3b2b2b2c` replaced independent per-pair anchor screening with a global cardinality-constrained minimum-cost matching lower bound. Each remaining same-attribute candidate `(u,v)` is charged the exact number of adjacency disagreements it would create against the already inventory-forced anchors. For any complete feasible partial alignment, the sum of these charges is exactly the anchor-to-remaining part of the common-edge disagreement count, while remaining-to-remaining disagreements are omitted. Therefore the minimum cost over every size-`need` assignment is a sound lower bound on the total remaining disagreement budget.

The implementation uses successive shortest augmenting paths for minimum-cost bipartite matching. A candidate pair from a directly verified feasible witness is certified forced only if forbidding it either destroys the required matching cardinality or pushes the global lower bound over the declared edge-disagreement budget. This is strictly stronger than rev90's per-pair test: a constructed case has all four duplicate-bucket candidate pairs individually within budget, but only one assignment has aggregate cost within budget; both duplicate identities become certifiably forced.

Validation: **4 passed**. The min-cost matcher exactly matched brute-force optimum on **500 random bipartite graphs** up to 4x4. An independent full-alignment oracle over **350 random graph pairs** found no released pair outside the intersection of all truly budget-feasible alignments. A separate case proves inconsistency where every individual candidate passes the budget but every required aggregate assignment exceeds it.

The unrestricted leaf is not fully solved because remaining-to-remaining disagreements are still omitted from this first lower bound. It is decomposed into:

- `...ca`: aggregate anchor-to-remaining assignment lower bound with exclusion forcing — `solved_v0_1`;
- `...cb`: add safe lower bounds for remaining-to-remaining structural disagreement, including partial matching — unresolved;
- `...cc`: avoid one min-cost re-solve per witness edge and improve feasible-witness recovery when the lower-bound minimizer itself violates internal-edge budget — unresolved.

Estimated active-node count: **472**, below prediction **512**.
