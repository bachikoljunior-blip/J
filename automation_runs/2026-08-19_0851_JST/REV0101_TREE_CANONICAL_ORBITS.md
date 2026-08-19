# rev101 — polynomial attributed-tree canonical/orbit certificate

Root remains **NOT_AGI**.

The broad general canonical-labeling leaf was attempted directly and decomposed after isolating a substantial exact graph family.

For an attributed tree, rev101 computes an AHU-style canonical form for the tree rooted at every vertex. Two vertices of the same attributed tree are in the same automorphism orbit exactly when their rooted canonical forms are equal. Across two isomorphic attributed trees, a source vertex can map exactly to the target vertices with the same rooted form. Hence an individual identity is forced precisely when its rooted form is a singleton orbit. This gives the exact forced-pair set without enumerating automorphisms.

A complete rooted-tree isomorphism witness is constructed by recursively matching child canonical forms and is directly checked against the full attribute and adjacency matrices before forced identities are released.

In-session validation:

- star: two orbits, with only the center singleton and therefore forced;
- 101-vertex path: 51 reflection orbits, with only the center singleton and forced;
- a repeated-attribute 9-vertex asymmetric tree: all 9 rooted forms are singleton, so every hidden-permutation pair is forced.

The previous general leaf `...c2d3b2b2b3c3c3` is decomposed into:

- `...c2d3b2b2b3c3c3a`: exact attributed-tree canonical/orbit certificate — `solved_v0_1`;
- `...c2d3b2b2b3c3c3b`: resource-bounded adaptive individualization/refinement canonical-orbit search with explicit completeness/limit certificates — unresolved;
- `...c2d3b2b2b3c3c3c`: worst-case general cyclic/high-connectivity canonical labeling and automorphism-group handling beyond current polynomial structural certificates — unresolved.

Estimated active-node count after decomposition: **484**, below prediction **512**.
