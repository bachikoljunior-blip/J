# rev93 — anchorless duplicate-attribute higher-order reasoning attempt

Root remains **NOT_AGI**.

Directly attacking the whole anchorless partial-edit problem at once was not justified, so the unresolved leaf `...c2d3b2b2b3` is decomposed into narrower children.

Implemented a polynomial higher-order fallback for the exact/full subcase using joint 2-dimensional Weisfeiler–Leman refinement over ordered vertex pairs. Initial pair colors include both endpoint attributes, equality, and adjacency. Each refinement round colors `(i,j)` using its current pair color plus the multiset of `(color(i,k), color(k,j))` over all intermediate vertices `k`. Vertex identities are inferred only from diagonal pair colors, and only when every diagonal color class is singleton in both graphs with matching inventories. The induced bijection is then directly checked against the complete attribute matrix and adjacency matrix before release.

This path is strictly fail-closed: persistent non-singleton classes release no identities, so automorphic graphs such as cycles remain ambiguous rather than being assigned arbitrarily.

Validation mirrored in-session:

- A 12-vertex 3-regular anchorless graph with identical attributes leaves all vertices in one 1-WL class, but joint 2-WL produces singleton diagonal classes and recovers the exact hidden permutation after direct verification.
- A 10-cycle remains ambiguous and releases no identities.
- A same-size perturbed non-isomorphic graph does not produce a certified mapping.

The anchorless parent remains unresolved and is decomposed into:

- `...c2d3b2b2b3a`: exact/full anchorless duplicate-attribute alignment resolved by higher-order 2-WL when diagonal classes become singleton, with direct verification — `solved_v0_1`;
- `...c2d3b2b2b3b`: anchorless partial-edit alignment/forced-pair certificates under insertion/deletion and edge-disagreement budgets using higher-order/global constraints — unresolved;
- `...c2d3b2b2b3c`: intrinsic-symmetry/orbit certificates that can prove no identity is forced (or isolate forced orbits) without arbitrary symmetry breaking — unresolved.

Estimated active-node count after decomposition: **472**, below prediction **512**. Whole-tree transversal/rewrite remains inactive.
