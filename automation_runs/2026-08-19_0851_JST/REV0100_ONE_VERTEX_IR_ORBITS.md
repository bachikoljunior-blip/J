# rev100 — one-vertex individualization/refinement orbit enumeration

Root remains **NOT_AGI**.

Resolved leaf `...c2d3b2b2b3c3c2` at `solved_v0_1` for the one-vertex-individualization-discrete regime.

For a chosen source base vertex, every exact attributed isomorphism must map it to some target vertex with the same persistent attribute. rev100 tries every such target. The source and target seeds receive a distinguished color and joint 1-WL refinement is run. If the individualized color inventories differ, that seed target is impossible. If all classes become singleton, there is exactly one color-preserving candidate mapping; it is directly verified against every attribute and adjacency entry. If that candidate fails, the seed target is also impossible. A seed target whose matching color inventory remains non-singleton is treated as unresolved, not guessed.

When one source base vertex has every possible target resolved in this way, the directly verified mappings are the complete exact-isomorphism family: every isomorphism must choose one of those base images, and each base image has at most the unique discrete color-preserving mapping. The intersection of this complete mapping family is therefore the exact forced-pair set.

In-session validation used the 12-vertex 3-regular repeated-attribute graph from rev93. Ordinary 1-WL leaves all vertices ambiguous, but individualizing one vertex makes all 12 colors singleton. Across every possible target image exactly one directly verified isomorphism survives and the hidden permutation is recovered. A 30-cycle remains non-discrete after one seed and correctly returns `undetermined_refinement_depth` with no released identity.

The remaining general scalable canonical/orbit leaf is `...c2d3b2b2b3c3c3`.

Active problem count remains **481**, below prediction **512**.
