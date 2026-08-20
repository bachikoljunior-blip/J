# rev202 uniform-neighborhood Johnson/relation provenance audit

Run identity: `chatgpt-session-immediate-20260820T085307+0900-06aca83f`  
Execution start: `2026-08-20T08:53:07+09:00`  
Session starting main: `06aca83ffef7e644ae63421514cfab8c2fe0c2ea`  
AGI-GI transition: `rev201 -> rev202`

## Scope and strict status

rev201 solves paired provenance only when exact degree/color signatures split the right part. rev202 handles a finite, theorem-faithful portion of the homogeneous-signature residual: the left neighborhoods form a uniform hypergraph on the right ground.

The result is a local structural provenance certificate. It is not the Design Lemma, coherent Split-or-Johnson, an ambient transporter, a full string-isomorphism set, recurrence closure, or AGI. `AGI = NOT_AGI`; the root remains unresolved.

Problem-count policy remains **predicted 512 / effective 512**. The active H6-R3b leaf is replaced in place; no count-overrun rewrite is triggered.

## Existing-world object and cross-layer mapping

The implementation follows the explicit construction in H. A. Helfgott, J. Bajpai, D. Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574, Proposition 5.7 proof:

- after selecting a large twin-free same-degree left cell, its neighborhoods are a uniform hypergraph on `V2`;
- complement when the common degree exceeds `|V2|/2`;
- a complete uniform family gives an explicit Johnson coordinate system;
- otherwise use arity `d = min(d1, 6 ceil(log(|V1|)/log(|V2|)))`;
- when `d=d1`, the relation is membership in the hyperedge family; when `d<d1`, the color of a distinct `d`-subset is its exact containment count in hyperedges.

rev202 maps this at several layers:

1. **Incidence layer:** validate all endpoints, exact common nontrivial left degree, and pairwise distinct neighborhoods.
2. **Normalization layer:** complement every neighborhood exactly when the common degree is greater than half the right ground; equality is left uncomplemented deterministically.
3. **Johnson layer:** compare against the full set of `d1`-subsets and emit the explicit left-vertex-to-right-subset coordinate table.
4. **Relation layer:** materialize every right `d`-subset, its exact containment count, the full color classes, and multiplicity inventory.
5. **Paired provenance layer:** source and target must agree on outcome type, degree normalization, arity, and every relation-color multiplicity. Mismatch is an exact necessary-invariant failure.
6. **Resource/safety layer:** exceeding the explicit subset cap, nonuniform degrees, trivial degrees, twins, and homogeneous containment residuals remain typed fail-closed outcomes.
7. **Boundary layer:** actual relation transport, Design/coherent descent, ambient group cost, and full parent-string intersection are not inferred from matching inventories.

## Solved child and remaining decomposition

Solved local child:

> Mechanically derive the exact uniform-neighborhood Johnson or nonconstant containment-relation object, and pair its necessary invariants across source and target.

The H6-R3 parent remains unresolved and is refined in place:

- **H6-R3a — degree/color signature provenance:** solved by rev201.
- **H6-R3b1 — uniform-neighborhood Johnson/relation provenance:** solved by rev202.
- **H6-R3b2 — relation twin partition:** compute the exact twin relation of the derived `d`-ary right relation and produce a canonical proper restriction when a large twin class exists.
- **H6-R3c — Design/coherent provenance:** run exact WL/Design machinery on the nonconstant relation and tie the result back to the parent incidence state.
- **H6-R4 — ambient paired transport:** lift Johnson/relation structure through the parent group action.
- **H6-R5 — exact full-string integration:** intersect every surviving structural branch with the complete source/target incidence strings.
- **H6-C1 — recurrence closure:** certify cost and progress on every edge, including cost-free one-vertex descent versus post-branching constant-factor descent.

The next unresolved leaf is **H6-R3b2, exact relation-twin partition and proper paired restriction**.

## Verification

Command:

```text
python -m pytest -q test_uniform_neighborhood_relation_provenance_rev202.py
```

Result: `6 passed`.

Coverage includes:

- complete `2`-uniform family on four points -> explicit Johnson embedding;
- noncomplete cycle hypergraph -> exact nonconstant pair relation;
- true degree-3-to-degree-2 complement normalization on five points;
- all `4! x 4! = 576` left/right relabelings of the relation regression;
- duplicate-neighborhood twin failure;
- exact subset-materialization resource failure.
