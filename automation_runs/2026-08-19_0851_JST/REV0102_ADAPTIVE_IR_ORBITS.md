# rev102 — resource-bounded adaptive IR orbit search

Root remains **NOT_AGI**.

Resolved leaf `...c2d3b2b2b3c3c3b` at `solved_v0_1` as an exact, explicitly resource-bounded fallback.

At each search node, all previously individualized source/target vertex pairs receive unique marks and joint 1-WL refinement is run. If color inventories differ, the branch is impossible. If the partition becomes discrete, the unique color-preserving mapping is directly checked against the complete attribute and adjacency matrices. Otherwise the smallest non-singleton source color class is selected, one source vertex is individualized, and every target vertex in the corresponding color class is branched. Every exact isomorphism follows exactly one such branch, so completing the tree enumerates the complete exact-isomorphism family.

The algorithm tracks an explicit state limit and witness limit. If those limits are reached while the verified-witness intersection is nonempty, no identities are released. As in the previous orbit certificates, an empty intersection of already verified isomorphisms is sufficient to prove that no pair is globally forced even before the remaining search finishes.

In-session validation:

- 12-cycle: 6 search states and 3 directly verified mappings are enough for the mapping intersection to become empty, certifying no forced identity;
- 12-node regular asymmetric repeated-attribute graph: 13 states, maximum individualization depth 1, one verified isomorphism, complete enumeration, and the entire hidden permutation certified;
- deliberately tiny state limits return `undetermined_search_limit` with no released identities.

This is a practical exact fallback with explicit completeness certificates, but its state count is not guaranteed polynomial on worst-case general graphs. The remaining leaf is therefore the stricter worst-case scalable canonical-labeling/automorphism problem `...c2d3b2b2b3c3c3c`.

Active problem count remains **484**, below prediction **512**.
