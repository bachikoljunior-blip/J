# rev206 bipartite neighborhood/coset intersection audit

## Scope, count, and strict state

rev205 closes the right-ground ambient alignment-domain child for the complete rev204 Design witness cover. It does not yet intersect each surviving right coset with the original bipartite incidence state. rev206 attacks that next boundary without claiming the full parent action unless its left-side premise is separately certified.

The predicted/effective problem count remains **512 / 512**. This work replaces the existing H6-R3c2b internal leaf in place; it does not add a new active global branch. `AGI = NOT_AGI` and the W1R-H6 parent remains unresolved.

## Existing-world mechanism checked across layers

The implementation follows the String Isomorphism/coset framework rather than inventing a second solver:

- L. Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547: GI, String Isomorphism under group action, and Coset Intersection are treated in one group-action framework; canonical combinatorial structures restrict the ambient search rather than replace the original string.
- H. A. Helfgott, J. Bajpai, D. Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574: the corrected Split-or-Johnson exposition keeps the output inside the ambient isomorphism/coset recurrence.

The repository already has the exact software analogues needed here: `RightCoset`, Schreier chains, `candidate_coset_string_isomorphism_u2`, and the action-agnostic `paired_action_coset_preimage_v1`. rev206 composes them rather than enumerating the ambient right group.

## Exact local model

For a candidate right coset `H*r`, assume the left action is the full product of symmetric groups inside the supplied left-color classes. Then a right permutation is a full colored-bipartite isomorphism exactly when it sends, color by color, the multiset of source left neighborhoods to the target neighborhood multiset.

`bipartite_neighborhood_coset_intersection_v1.py` realizes that equivalence mechanically:

1. Validate the source/target left-color inventories. A mismatch is exact empty.
2. Move every source neighborhood through the fixed candidate representative `r`.
3. Starting from those shifted source neighborhoods and the target neighborhoods, build their complete orbit closure under the candidate subgroup `H`, with an explicit fail-closed state cap.
4. Let `H` act on this finite subset domain. Each subset coordinate receives the exact multiplicity vector of left colors whose neighborhood equals that subset.
5. Solve this induced exact string isomorphism inside the image of `H` with the existing candidate-coset SI machinery.
6. Lift a nonempty image coset through the already-proved generic paired Schreier preimage, recovering the complete right-ground subgroup fiber without enumerating `H`.
7. Restore the fixed representative `r`, yielding an exact subcoset of the original rev205 candidate.

The result preserves repeated neighborhoods and left-color multiplicities; it is not merely a set-family comparison.

## Boundary discovered by the attempt

The mathematical local model is exact, but the current rev199-rev205 parent provenance does not yet mechanically certify that the actual parent permits the **full color-symmetric left action**. rev201 proves color-preserving structural provenance, not equality of the parent left subgroup with the full product of symmetric groups. Therefore rev206 exposes `parent_left_action_verified` only as metadata and deliberately does not use it to manufacture a theorem claim.

Consequently the current H6-R3c2b leaf is refined in place:

- **H6-R3c2b1 — exact right-coset / colored-neighborhood intersection:** solved by rev206 for the full color-symmetric-left model.
- **H6-R3c2b2 — actual parent left-action provenance:** recover the parent left subgroup/coupling and prove when it reduces to the rev206 model; otherwise construct the coupled left/right transporter rather than silently relaxing the group.
- **H6-R3c2b3 — complete witness union integration:** apply the certified full-parent intersection to every rev205 witness coset and prove the resulting union is exactly the parent isomorphism set.
- **H6-C1 — recurrence closure:** only after b2/b3, connect nonempty children to the split/block/UPCC recurrence with proof-carrying shrink and quasipolynomial accounting.

This decomposition is a cross-layer simplification: the induced subset-action string and generic image/preimage machinery solve neighborhood multiplicities, repeated rows, right-group restriction, and exact coset reconstruction in one shared primitive. What remains is the genuinely separate parent left-group coupling obligation.

## Non-claims

rev206 does not claim that the parent left action is full color-symmetric, does not yet union all rev205 witness branches, and does not certify the artificial subset-image degree as a global quasipolynomial recurrence charge. Resource overflow and unresolved image SI remain fail closed. Full Split-or-Johnson closure, global W1R-H6 recurrence closure, generality/performance/autonomy proof, practical AGI delivery, and AGI are all unclaimed.
