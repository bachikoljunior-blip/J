# rev206 exact bipartite/coset intersection audit

## Scope, count, and strict state

rev205 closes the right-ground ambient alignment-domain child for the complete rev204 Design witness cover. It does not yet intersect each surviving right coset with the original bipartite incidence state. rev206 attacks that boundary at two layers: first an exact right-side neighborhood-family model, then a stronger exact intersection that preserves the actual coupled parent permutation action.

The predicted/effective problem count remains **512 / 512**. This work replaces the existing H6-R3c2b internal leaf in place; it does not add a new active global branch. `AGI = NOT_AGI` and the W1R-H6 parent remains unresolved.

## Existing-world mechanism checked across layers

The implementation follows the String Isomorphism/coset framework rather than inventing a second solver:

- L. Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547: GI, String Isomorphism under group action, and Coset Intersection are treated in one group-action framework; canonical combinatorial structures restrict the ambient search rather than replace the original string.
- H. A. Helfgott, J. Bajpai, D. Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574: the corrected Split-or-Johnson exposition keeps structural progress inside the ambient isomorphism/coset recurrence and later lifts solved image actions back to the original group.

The repository already has exact software analogues: `RightCoset`, Schreier chains, `candidate_coset_string_isomorphism_u2`, and the action-agnostic `paired_action_coset_preimage_v1`. rev206 composes them rather than enumerating the ambient group.

## Layer 1: exact neighborhood-family intersection

For a candidate right coset `H*r`, if the left action is the full product of symmetric groups inside supplied left-color classes, a right permutation is a full colored-bipartite isomorphism exactly when it sends, color by color, the multiset of source left neighborhoods to the target neighborhood multiset.

`bipartite_neighborhood_coset_intersection_v1.py` realizes that equivalence mechanically:

1. validate source/target left-color inventories;
2. move source neighborhoods through the fixed candidate representative `r`;
3. build the complete orbit closure of source/target neighborhoods under `H`, with an explicit state cap;
4. encode at each subset coordinate the exact multiplicity vector of left colors;
5. solve the induced string in the image of `H` with existing candidate-coset SI;
6. lift the image coset with generic paired Schreier preimage;
7. restore `r` and return an exact subcoset of the original right candidate.

Repeated neighborhoods and left-color multiplicities are preserved exactly. The regression suite compares the returned S4 coset with direct exhaustive colored-bipartite semantics.

## Layer 2: preserve the actual coupled parent action

The first model exposed a real theorem boundary: rev201 proves color-preserving structural provenance but does not imply that the actual parent left subgroup is a full symmetric product. Treating left and right permutations independently could therefore admit false isomorphisms.

`bipartite_parent_action_coset_intersection_v1.py` removes that relaxation whenever the caller supplies the actual parent `StabilizerChain` and the generator-paired parent-to-right action already needed by rev205:

1. take a rev205 right structural candidate coset and recover its **exact preimage in the parent group** using `paired_action_coset_preimage`;
2. keep the resulting parent subgroup and representative coupled—no independent left/right product group is introduced;
3. construct its exact induced action on a disjoint auxiliary domain containing every left vertex, every right vertex, and every cross pair `L x R`;
4. encode the complete colored bipartite state on that domain: left colors, right colors, and every edge/nonedge bit;
5. shift the source auxiliary string through the fixed parent-candidate representative;
6. run existing candidate-coset String Isomorphism in the induced subgroup action;
7. lift the exact image result back through the same paired-action machinery and restore the fixed representative.

Thus the output is exactly the subset of the **actual parent group** that both projects into the supplied rev205 right alignment and maps the complete colored bipartite source state to the target state. A regression deliberately uses a diagonal S3 parent action: a right-only relabeling that would be accepted by independent left/right symmetric groups is correctly rejected by the coupled parent action. Other regressions compare the returned parent coset against direct exhaustive enumeration.

## Current solved boundary and remaining decomposition

The parent-action primitive solves the set-theoretic left/right coupling obligation generically, provided the caller supplies a certified generator-paired parent-to-right action. Therefore the active leaf is simplified in place:

- **H6-R3c2b1 — exact local right-neighborhood intersection:** solved for the full color-symmetric-left model; retained as a reusable lower-dimensional specialization.
- **H6-R3c2b2 — exact coupled parent-action intersection primitive:** solved by the parent preimage + complete bipartite auxiliary action described above.
- **H6-R3c2b3 — complete rev205 witness-union wiring:** unresolved. The rev204/rev205 complete witness family must be invoked with the actual parent-to-right generator pairing, every surviving structural coset must pass through the coupled parent-action primitive, and the resulting exact children must be reconstructed as the complete parent isomorphism set without dropping a branch.
- **H6-C1 — recurrence closure:** unresolved. The complete auxiliary domain has size `|L|+|R|+|L||R|`; rev206 certifies exactness but deliberately does not yet count that artificial degree as a valid quasipolynomial recurrence shrink/cost. A lower-dimensional implementation or an explicit cost transfer proof is still required before global accounting accepts the edge.

This is a cross-layer reduction in problem count rather than branch growth: neighborhood multiplicities, duplicate rows, right structural restriction, actual left/right coupling, and coset reconstruction now share the same image/preimage + candidate-SI substrate. The remaining leaf is primarily complete family wiring plus cost/progress certification.

## Non-claims

rev206 does not yet union all rev205 witness branches and does not certify the quadratic auxiliary action as a globally admissible quasipolynomial recurrence edge. Resource overflow, invalid parent/right generator pairing, non-preserved bipartitions, or unresolved induced SI remain fail closed. Full corrected Split-or-Johnson closure, global W1R-H6 recurrence closure, generality/performance/autonomy proof, practical AGI delivery, and AGI are all unclaimed.
