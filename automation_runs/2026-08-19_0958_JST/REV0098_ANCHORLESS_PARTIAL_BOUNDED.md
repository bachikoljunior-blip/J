# rev98 — anchorless partial/positive-budget exact forcing (bounded)

Root remains **NOT_AGI**.

Implemented exact bounded intersection over every attribute-preserving minimum-cardinality partial mapping whose common-edge disagreements fit the declared budget. Enumerating the minimum common size `k` is sufficient: every larger feasible map has a `k`-pair restriction with no greater disagreement, so a pair present in every feasible `k`-map is present in every feasible larger map. Search cutoff fails closed.

Focused regression: **4 passed**. The broad leaf remains unresolved at scale and is decomposed into `...b3c1` bounded exact enumeration (`solved_v0_1`) and `...b3c2` scalable branch-and-bound feasibility/exclusion reasoning (unresolved). Estimated active nodes: **480**, below 512.