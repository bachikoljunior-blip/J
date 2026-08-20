# rev206 exact bipartite/coset intersection audit

## Scope, count, and strict state

rev205 closes the right-ground ambient alignment-domain child for the complete rev204 Design witness cover. It does not yet intersect each surviving right coset with the original bipartite incidence state. rev206 closes that **set-theoretic full-string boundary** in three layers: a right-side neighborhood-family specialization, a coupled actual-parent action intersection, and complete reconstruction of the full rev204/rev205 witness union.

The predicted/effective problem count remains **512 / 512**. This work replaces the existing H6-R3c2b internal leaf in place; it does not add a new active global branch. `AGI = NOT_AGI` and the W1R-H6 parent remains unresolved because recurrence-safe cost/progress accounting is still separate.

## Existing-world mechanism checked across layers

The implementation follows the String Isomorphism/coset framework rather than inventing a second solver:

- L. Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547: GI, String Isomorphism under group action, and Coset Intersection are treated in one group-action framework; canonical combinatorial structures restrict the ambient search rather than replace the original string.
- H. A. Helfgott, J. Bajpai, D. Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574: the corrected Split-or-Johnson exposition keeps structural progress inside the ambient isomorphism/coset recurrence and later lifts solved image actions back to the original group.

The repository already has exact software analogues: `RightCoset`, Schreier chains, `candidate_coset_string_isomorphism_u2`, and the action-agnostic `paired_action_coset_preimage_v1`. rev206 composes them rather than enumerating the ambient group.

## Layer 1: exact neighborhood-family intersection

For a candidate right coset `H*r`, if the left action is the full product of symmetric groups inside supplied left-color classes, a right permutation is a full colored-bipartite isomorphism exactly when it sends, color by color, the multiset of source left neighborhoods to the target neighborhood multiset.

`bipartite_neighborhood_coset_intersection_v1.py` realizes that equivalence mechanically by closing the neighborhood subsets under `H`, encoding exact multiplicity-by-left-color on that invariant subset domain, solving the induced string in the image of `H`, lifting the image coset with generic paired Schreier preimage, and restoring `r`. Repeated neighborhoods and left-color multiplicities are preserved exactly. Small S4 regressions compare the returned coset with direct exhaustive semantics.

## Layer 2: preserve the actual coupled parent action

The first model exposed a theorem boundary: rev201 proves color-preserving structural provenance but does not imply that the actual parent left subgroup is a full symmetric product. Treating left and right permutations independently could admit false isomorphisms.

`bipartite_parent_action_coset_intersection_v1.py` removes that relaxation whenever the caller supplies the actual parent `StabilizerChain` and a generator-paired parent-to-right action:

1. recover the exact parent-group preimage of one rev205 right structural candidate with `paired_action_coset_preimage`;
2. retain the coupled parent subgroup/representative rather than introducing independent left/right groups;
3. form the induced action on all left vertices, all right vertices, and all cross pairs `L x R`;
4. encode the complete colored bipartite state: left colors, right colors, and every edge/nonedge bit;
5. solve the exact candidate-coset string in that induced subgroup action;
6. lift the result back through the coupled parent action and restore the fixed representative.

Thus each output is exactly the subset of the **actual parent group** that projects into the supplied rev205 right alignment and maps the complete colored bipartite source state to target. A diagonal-S3 regression deliberately checks a right-only relabeling that independent left/right symmetric groups would permit but the actual coupled parent action forbids; it is correctly exact-empty. Other regressions compare the returned parent coset against direct exhaustive enumeration.

## Layer 3: complete rev204/rev205 witness-union reconstruction

`bipartite_design_parent_union_v1.py` connects the previous layers to the entire structural cover rather than one branch:

1. generate the exact right image group from the parent generator pairing;
2. re-derive rev204 and rev205 from the original bipartite inputs, obtaining the complete first-successful Design witness cover inside that exact right image;
3. for every surviving right structural coset, invoke the coupled parent-action full-string intersection;
4. fail closed if even one branch is unresolved;
5. when every branch is exact, discard only exact-empty branches;
6. reconstruct the complete nonempty union as one parent right coset using one representative, every child target-automorphism subgroup, and all inter-branch representative differences, with mechanical checks that each generator/difference preserves the complete target bipartite state.

This mirrors the already-validated `design_tuple_full_string_union_si_v1` reconstruction argument, but on the actual parent bipartite action. Completeness comes from rev204's complete witness family, rev205's exact filtering inside the full right image of the parent group, and exact preimage/intersection of every survivor. Cycle-5 regressions verify that the complete structural cover reconstructs the full cyclic parent coset, that full parent colors can shrink it to the identity, that a color mismatch makes the entire union exact empty, and that an unresolved child resource cap withholds the union rather than sampling it.

## Current solved boundary and remaining decomposition

The set-theoretic H6-R3c2b obligations are now reduced in place:

- **H6-R3c2b1 — exact local right-neighborhood intersection:** solved for the full color-symmetric-left specialization.
- **H6-R3c2b2 — exact coupled parent-action intersection primitive:** solved.
- **H6-R3c2b3 — complete rev205 witness-union wiring and exact parent-isomorphism reconstruction:** solved, conditional only on the caller providing the certified generator-paired parent-to-right action that the wrapper explicitly validates.
- **H6-C1 — recurrence/cost closure:** unresolved. Each exact parent child currently uses a complete auxiliary action of degree `|L|+|R|+|L||R|`. This is only a polynomial blow-up in the current domain, so quasipolynomial solvability is plausibly preserved, but rev206 does **not** infer a recurrence certificate from that observation. The child SI accounting must be mechanically transferred back to the original root measure, branch multiplicity and rev204 witness cost must be charged, and the resulting structural edge must still satisfy the corrected Split-or-Johnson progress condition before global accounting accepts it.

This is a cross-layer simplification rather than branch growth: neighborhood multiplicities, duplicate rows, right structural restriction, actual left/right coupling, complete branch union, and coset reconstruction now share the existing image/preimage + candidate-SI substrate. The next active leaf is therefore primarily **H6-C1: recurrence-safe polynomial-blowup cost transfer plus strict progress certification for the complete parent Design union**.

## Non-claims

rev206 certifies exact set reconstruction, not global recurrence closure. It does not yet certify the quadratic auxiliary action as an admissible charged edge of the existing quasipolynomial recurrence tree. Resource overflow, invalid parent/right generator pairing, non-preserved bipartitions, or unresolved induced SI remain fail closed. Full corrected Split-or-Johnson closure, global W1R-H6 recurrence closure, generality/performance/autonomy proof, practical AGI delivery, and AGI are all unclaimed.
