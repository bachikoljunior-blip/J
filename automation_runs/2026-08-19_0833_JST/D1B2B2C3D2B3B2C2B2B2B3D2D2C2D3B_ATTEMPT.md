# rev83 direct attempt — vertex insertion/deletion stability

Root remains **NOT_AGI**.

Implemented an a-posteriori feature-displacement certificate when an explicit injective alignment between common vertices is supplied and aligned continuous attributes agree within a declared tolerance. The certificate accounts for: (1) the global change in `1/sqrt(n)` normalization when graph size changes; (2) aligned common vertices whose structural color changes; (3) deleted vertices; and (4) inserted vertices. It bounds each depth block using `||phi(x)|| <= sqrt(2)` and combines depth bounds in quadrature.

Cumulative local regression rev75–83: **41 passed**, covering leaf insertion, induced-subgraph deletion, multiple inserted vertices with arbitrary incident edges, a nontrivial permutation plus insertion with explicit alignment, and fail-closed rejection of an attribute-inconsistent alignment.

The broad child is not solved because alignment inference and simultaneous attribute changes remain open. It is decomposed into:

- `...c2d3b1`: explicit-alignment insertion/deletion certificate with fixed common attributes — unresolved pending dedicated theorem/stress validation;
- `...c2d3b2`: infer a partial common-node alignment without assuming the answer — unresolved;
- `...c2d3b3`: combine vertex edits with bounded common-node attribute perturbations — unresolved.

Estimated active-node count after decomposition: **454**, below prediction 512.
