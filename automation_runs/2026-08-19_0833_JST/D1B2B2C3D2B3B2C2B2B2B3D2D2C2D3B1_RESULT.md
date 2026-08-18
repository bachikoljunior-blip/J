# rev84 result — explicit-alignment vertex insertion/deletion certificate

Status: **solved_v0_1 for this scoped child**. Root remains **NOT_AGI**.

For each depth, aligned common vertices with unchanged color contribute only through the normalization difference `|1/sqrt(n)-1/sqrt(m)|`; aligned vertices whose structural color changes can move between orthogonal color buckets; deleted and inserted vertices contribute only on their respective sides. Since each RFF node vector has norm at most sqrt(2), the implemented depthwise triangle bound is deterministic, and combining direct-sum depths in quadrature yields the full feature-displacement certificate.

Dedicated stress validation exhaustively enumerated all 64 simple graphs on four common labeled vertices and all 16 possible neighborhoods of one inserted vertex, checking both insertion and the reverse deletion: **2,048 certificate directions**. All passed. Cumulative local pytest count: **42 passed**.

The certificate requires a supplied injective common-node alignment and unchanged aligned attributes. Alignment inference and joint attribute perturbation remain unresolved children.
