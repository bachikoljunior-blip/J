# rev81 direct attempt — bounded structural-edit stability

Root remains **NOT_AGI**.

For fixed node identities and fixed continuous attributes, an undirected edge toggle can change a depth-h 1-WL structural color only within h hops of an edited edge endpoint. Using the union of the before/after graphs gives a conservative support set. Because every RFF node vector has norm at most sqrt(2), moving one affected node between two orthogonal color buckets changes a depth block by at most 2 before the `1/sqrt(n)` normalization. If `r_h` is the conservative support size at depth h, the full H+1-depth feature displacement is therefore bounded by

`2/sqrt(n) * sqrt(sum_h r_h^2)`.

The implementation validates that the observed changed-color set is contained in each claimed support and then checks the realized feature displacement against the deterministic bound. Cumulative local regression rev75–81: **35 passed**.

This direct attempt does not cover all meanings of structural edit, so the broad child remains unresolved and is decomposed into:

- `...c2d3a`: simple-undirected edge toggles with fixed node identities/attributes — unresolved pending dedicated theorem leaf validation;
- `...c2d3b`: node insertion/deletion with explicit or inferred alignment — unresolved;
- `...c2d3c`: directed, typed or weighted edge edits — unresolved;
- `...c2d3d`: structural edits when node correspondence itself is unknown — unresolved.

Estimated active-node count after decomposition: **451**, still below prediction 512.
