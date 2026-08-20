# rev200 visible bipartite twin-split progress

Scope: AGI-GI W1R-H6 only. AGI remains `NOT_AGI`.

## Problem-tree accounting

Predicted problem count: **512**. Active problem count: **512**. The count is not increased: rev200 replaces an internal child of W1R-H6 in place.

Selected unresolved leaf after rev199: the exact bipartite Split-or-Johnson input gate is mechanically checkable, but the theorem conclusion / recursive progress is still not represented by proof-carrying code.

## Existing-world check

Primary sources checked for this layer:

- Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547, Split-or-Johnson section: https://arxiv.org/abs/1512.03547
- Babai, January 2017 correction notice for the Split-or-Johnson recursive call: https://people.cs.uchicago.edu/~laci/update.html
- Helfgott–Bajpai–Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574, Split-or-Johnson exposition: https://arxiv.org/abs/1710.04574

The repository already records the corrected-theorem audit in rev198. The rev200 observation is deliberately narrower than the general theorem: whenever rev199 certifies its large-part symmetry defect *by exact left twin classes*, those same twin classes are already an explicit isomorphism-equivariant partition of the large side. Therefore, if their maximum size is within rev196's configured numeric shrink fraction, the branch can be charged as an independently certified `aux_shrink` without appealing to an unimplemented theorem conclusion.

## Implemented child

`bipartite_twin_split_progress_v1.py`:

- reuses rev199's exact bipartite gate;
- exposes the exact left twin partition and cell-size multiset;
- certifies constant-factor auxiliary shrink only when the rev199 theorem gate and the separate rev196 shrink gate both hold;
- gives a conservative polynomial local-cost charge;
- supplies an adapter that accepts only caller-provided recursive children whose auxiliary measures exactly match the twin-cell-size multiset;
- remains fail closed when the theorem gate does not fire or when the recurrence shrink threshold is not met.

This is real recursive progress for the stronger visible-twin subcase, not a proof of the corrected general Split-or-Johnson conclusion.

## New unresolved child

For theorem-gated instances not closed by the visible-twin shrink, implement the source/target-comparable bipartite recursive descent itself: maintain both colored parts under an exact transport relation, certify the corrected small-part reduction or an explicit Johnson embedding, and connect each produced child to the existing full-string SI plus rev196 accounting. No structural phase label may stand in for an independently checked recursive edge.
