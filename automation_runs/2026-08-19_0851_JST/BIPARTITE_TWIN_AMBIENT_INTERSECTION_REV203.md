# rev203 exact ambient right-coset intersection for unique twin maps

Scope: AGI-GI W1R-H6 only. AGI remains `NOT_AGI`.

Predicted/active problem count remains **512/512**. rev203 replaces the ambient-intersection child identified by rev202 in place.

## Cross-layer simplification

The initially obvious formulation was a generic intersection between rev202's product-of-symmetric-groups transport coset and an arbitrary ambient right coset. Re-reading the existing J substrate exposes a simpler exact reduction: `canonical_partition_transporter_v1.py` already computes an exact bounded transporter for an ordered partition inside an arbitrary permutation subgroup using a Schreier orbit/stabilizer construction. Once rev201 uniquely pairs the exact twin cells, the desired condition is *exactly* an ordered-partition transporter condition.

For an ambient `RightCoset(H,r)`, every candidate has repository form `compose(r,h)` with `h in H`. Such a candidate maps source twin partition S to target T iff `h` maps `r(S)` to T. Therefore no generic coset-coset intersection algorithm is needed for this child: run the existing exact transporter inside H from `r(S)` to T, then conjugate its exact source stabilizer to the target stabilizer and compose the ambient representative with the found H-transporter.

This also serves as a problem-tree cross-cut: it simultaneously discharges the graph-level internal-bijection ambiguity, the group-level ambient restriction, and the coset-level representation issue for the rev201 unique-quotient subcase, while avoiding factorial materialization of rev202's full cellwise family.

## Implemented progress

`bipartite_twin_ambient_coset_intersection_v1.py`:

- accepts only rev201 `exact_unique_twin_quotient_mapping` results;
- orders target twin cells according to the exact source->target quotient pairing;
- applies the ambient right-coset representative to the ordered source partition;
- invokes the existing exact `canonical_partition_transporter` inside the ambient subgroup on singleton quotient blocks;
- returns exact empty when the ordered target partition is outside that subgroup orbit;
- remains fail closed on partition-orbit state-cap exhaustion;
- on success, conjugates the exact source stabilizer to `H ∩ Stab(T)`, forms one complete `RightCoset`, and mechanically checks representative/coset conventions and ordered-cell preservation;
- works for a nontrivial ambient right-coset offset, not only an ambient group.

The regression compares the result against rev202's complete eight-element unconstrained twin-cell family, checks a strict two-element ambient subcoset, exact empty in the trivial ambient group, state-cap fail-closed behavior, and refusal to guess ambiguous rev201 quotient-cell pairings.

## New unresolved child

Connect the exact rev203 ambient candidate coset to the **actual full-string SI** at the W1R-H6 caller boundary, including source/target bipartite structure provenance, exact empty propagation, candidate-coset string filtering, and rev196 recurrence accounting. The wrapper must not treat the unique-twin subcase as the corrected general Split-or-Johnson theorem: ambiguous rev201 quotient classes still require bounded canonical branching or the deeper theorem-faithful recursion/Johnson-output path.
