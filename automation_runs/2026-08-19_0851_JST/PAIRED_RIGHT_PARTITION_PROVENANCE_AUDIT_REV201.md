# rev201 paired right-partition provenance audit

Run identity: `chatgpt-session-immediate-20260820T085307+0900-06aca83f`  
Execution start: `2026-08-20T08:53:07+09:00`  
Session starting main: `06aca83ffef7e644ae63421514cfab8c2fe0c2ea`  
AGI-GI transition: `rev200 -> rev201`

## Scope and strict status

rev200 solved a local Exercise 5.5 restriction only relative to a supplied ordered right partition. It did not prove that source and target obtain compatible ordered cells. rev201 addresses that antecedent for the conservative degree/color-signature subcase.

The result is not full parent provenance, full Bipartite Split-or-Johnson, exact ambient string isomorphism, recurrence closure, or AGI. `AGI = NOT_AGI`; the root problem remains unresolved.

Problem-count policy remains **predicted 512 / effective 512**. This replaces the active H6-R3 subleaf in place; the overrun rewrite trigger is not active.

## Existing-world object and cross-layer mapping

The primary Split-or-Johnson exposition explicitly uses degree differences as a canonical partition before the higher-arity relation/Design cases, and requires canonical choices throughout:

- H. A. Helfgott, J. Bajpai, D. Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574, Proposition 5.7 proof: https://arxiv.org/abs/1710.04574
- L. Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547: https://arxiv.org/abs/1512.03547

rev201 realizes the existing idea at several layers:

1. **Local structural layer:** each right vertex receives the exact signature `(right input color, neighbor counts by canonically ordered left input color)`.
2. **Canonical representation layer:** supported typed color atoms receive an injective, totally ordered encoding; opaque objects are rejected instead of ordered by unstable `repr` or object identity.
3. **Partition layer:** signature classes are ordered by the exact encoding. Among all boundaries, the boundary minimizing the larger side is selected; ties use the boundary index. Vertex labels do not enter the decision.
4. **Paired provenance layer:** source and target must have identical left-color inventory and identical ordered right-signature inventory, including multiplicities. A mismatch is an exact color-preserving non-isomorphism invariant.
5. **rev200 composition layer:** the exact restriction certificate is run independently on source and target. A complete single restriction branch is emitted only when statuses, selected side, restricted twin bounds, Exercise 5.5 gates, and alpha-shrink flags agree.
6. **Ambient-action layer:** the certificate proves only that every color-preserving bipartite isomorphism maps the selected source signature union to the selected target signature union. Constructing the ambient transporter and intersecting the full parent strings remain separate obligations.

## Solved child and fail-closed boundary

Solved local child:

> For the degree/color-signature subcase, derive compatible ordered right partitions on source and target and certify a complete single selected restriction branch before invoking an ambient transporter.

Fail-closed boundary:

- one right signature class yields `canonical_right_partition_no_progress`;
- higher-arity Design/coherent information is not inferred from homogeneous degree/color data;
- unsupported color representations are rejected;
- equal degree inventories with unequal restricted twin invariants are rejected as an exact mismatch;
- no candidate is called a full isomorphism set.

## Recursive decomposition after the attempt

The general H6-R3 parent remains unresolved and is refined in place:

- **H6-R3a — degree/color signature provenance:** solved by rev201.
- **H6-R3b — higher-arity provenance:** derive a canonical right relation when all degree/color signatures are homogeneous, including exact relation-color multiplicities.
- **H6-R3c — coherent provenance:** connect a nonconstant right relation to the parent coherent configuration without caller booleans.
- **H6-R4 — ambient paired transport:** compute the exact ambient transporter coset for the selected source/target right union.
- **H6-R5 — full-string integration:** intersect the structural candidate with the complete parent incidence/string state and reconstruct exact empty/coset output.
- **H6-C1 — recurrence closure:** distinguish cost-free proper descent from post-branching constant-factor progress on every edge.

The next unresolved leaf is **H6-R3b higher-arity provenance for the homogeneous degree/color residual**.

## Verification

Command:

```text
python -m pytest -q test_paired_bipartite_right_partition_provenance_rev201.py
```

Result: `6 passed`.

Coverage includes:

- all `4! x 4! = 576` relabelings of a colored bipartite instance;
- exact signature-inventory mismatch;
- homogeneous no-progress behavior;
- rejection of opaque color objects;
- equal degree-signature inventory but unequal restricted twin invariants.
