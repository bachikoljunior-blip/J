# rev91 — scalable essential-edge detection

Root remains **NOT_AGI**.

The previous positive-budget certificate identified structurally forced candidate edges by recomputing a maximum matching once for every matched edge. That bottleneck was replaced with a single residual-network strongly-connected-component analysis.

A maximum bipartite matching is represented as a unit-capacity max flow. Any second maximum matching differs from the first by an integral circulation in the residual network. Therefore a currently matched edge can be removed by another maximum matching exactly when its reverse residual arc lies on a directed residual cycle. Equivalently, its left and right endpoints lie in the same residual SCC. Matched edges whose endpoints lie in different SCCs are present in every maximum matching.

Local validation: **3 tests passed**, including **1,200 random bipartite graphs up to 4x4** compared with exhaustive enumeration of all maximum matchings. Maximum-cardinality values and the complete essential-edge sets matched the oracle in every case.

Leaf `...c2d3b2b2b2b` is therefore `solved_v0_1` for exact essential-edge extraction in the candidate-superset matching layer. It does not address total edge-error assignment costs or the soundness of the candidate superset itself; those remain separate unresolved leaves.
