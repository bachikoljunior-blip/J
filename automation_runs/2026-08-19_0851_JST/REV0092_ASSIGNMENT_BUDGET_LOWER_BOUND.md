# rev92 — total disagreement assignment lower bound

Root remains **NOT_AGI**. No AGI achievement is claimed.

Resolved leaf `D1b2b2c3d2b3b2c2b2b2b3d2d2c2d3b2b2b2c`: incorporate the total remaining disagreement budget into assignment lower bounds rather than screening each candidate pair independently.

The previous positive-budget path assigned each remaining same-attribute candidate `(i,j)` a disagreement count against already-forced anchors, but only rejected the pair when that *individual* count exceeded the full budget. This could retain a candidate graph in which every individual edge looked affordable while every required multi-pair assignment exceeded the total budget.

rev92 adds an exact min-cost cardinality bipartite-matching primitive using successive shortest augmenting paths. Edge costs are the exact anchor-disagreement counts. For any requested remaining cardinality, the minimum matching cost therefore counts the least possible total disagreement against already-forced anchors. Disagreements among non-anchor matched pairs are deliberately omitted, so this value is a sound lower bound on the complete common-edge disagreement objective.

Candidate edges are now retained only when a cardinality-required assignment containing that edge has lower-bound cost within the remaining budget. Thus every truly feasible alignment is still contained in the resulting candidate graph, while collectively unaffordable assignments are pruned. SCC essential-edge extraction from rev91 is then applied only when the candidate graph's maximum cardinality equals the required cardinality. The min-cost assignment is used only as a candidate witness and is directly checked against the full pairwise edge-disagreement budget before any identities are released.

Validation performed in-session against independent exhaustive enumeration:

- 1,500 random bipartite cost instances up to 4x4: minimum cardinality-matching cost and budget-feasible edge set matched brute force exactly.
- A constructed integration case where every individual candidate costs 1 but two remaining matches are required under total budget 1 is now rejected by lower bound 2; the previous per-pair screen would retain all candidates.
- 500 random graph-alignment instances up to 4x4 were exhaustively enumerated under the full attribute/unmatched/edge-disagreement constraints. 81 identity pairs were released across the sample and no released pair lay outside the true forced-pair intersection.
- Existing representative positive-budget cases (permuted duplicate buckets, one real edge disagreement, symmetric cycle abstention) were mirrored in-session and preserved expected fail-closed behavior.

The positive-budget structural-forcing child `...c2d3b2b2b2` is therefore `solved_v0_1` at this conservative exact-attribute/edge-budget certificate level. Its three decomposed children (superset forcing/direct witness, scalable essential-edge extraction, and total assignment lower bound) are now all solved at v0.1.

The enclosing duplicate-attribute structural-forcing parent remains unresolved because its separate anchorless/global-symmetry child `...c2d3b2b2b3` is still open.

Active problem count remains **469**, below the prediction **512**; whole-tree transversal/rewrite is not triggered.
