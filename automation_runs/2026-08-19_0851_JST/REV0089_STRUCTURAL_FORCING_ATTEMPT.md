# rev89 direct attempt — structural forcing inside duplicate-attribute buckets

Root remains **NOT_AGI**.

Implemented iterative exact adjacency-to-forced-anchor refinement for the zero common-edge-disagreement case. The routine begins only from pairs already forced by exact-attribute capacity. It then partitions remaining same-attribute nodes by their exact adjacency vectors to the currently forced anchors. A singleton refined pair is added only when excluding it would reduce the remaining compatible capacity below the required common-node count. Newly forced pairs become anchors for the next round. Before any identities are released, a complete common-subgraph witness is constructed and every mapped attribute and common edge is directly verified.

Focused local regression: **3 passed**. A 14-node path with one unique endpoint attribute and all remaining nodes sharing one attribute propagates the unique anchor through the entire permuted path. An anchorless symmetric cycle releases no pairs. Across **500 random small zero-edge-edit cases**, every released pair was a subset of the forced-pair set from an independent exhaustive oracle.

The parent remains unresolved and is decomposed into:

- `...c2d3b2b2b1`: anchor-seeded structural forcing for exact attributes with zero common-edge disagreement — `solved_v0_1`;
- `...c2d3b2b2b2`: sound structural forcing when a positive common-edge disagreement budget is allowed — unresolved;
- `...c2d3b2b2b3`: anchorless duplicate-attribute cases requiring higher-order/global symmetry reasoning — unresolved.

Estimated active-node count after decomposition: **466**, below prediction 512.
