# Rev320 — Johnson construction cost binding

## Scope

This revision is the collision-resistant re-scope of the earlier superseded rev292/rev294 cost-binding attempts. It closes one accounting interface between two separately owned corrected Split-or-Johnson leaves without modifying either sibling implementation.

- rev287 constructs and certifies the exact `J(v,k) -> v` relational reduction and retains `construction_work_bound` together with the canonical Johnson incidence data and induced ground generators.
- rev291 consumes a relational-reduction-shaped object and charges `log2(max_multiplicative_cost)` before admitting the `C(v,k) -> v` auxiliary shrink into main recurrence accounting.
- rev320 validates the retained rev287 certificate structure and its exact deterministic work formula, then replaces a potentially unit source cost with a conservative finite power-of-two upper bound at least as large as both the retained construction work and the source cost bound.

The source `reduction_identity` is preserved unchanged. A separate `cost_binding_identity` commits to the cost-binding inputs and output bound.

## Fail-closed checks

The adapter rejects malformed schema/status/certification flags, malformed Johnson parameters, failure of `C(v,k) -> v` progress, invalid source cost bounds, non-SHA256 reduction identities, incomplete or noncanonical Johnson vertex subsets, incidence stars inconsistent with the retained canonical subsets, invalid induced ground permutations, and any mismatch between `construction_work_bound` and rev287's retained formula

`(2 + 2*g) * C(v,k) * k + g * C(v,k) + v`,

where `g` is the number of retained induced ground generators.

The finite handoff cost is the larger of the source upper bound and the next power of two above the deterministic construction-work bound. This avoids downward floating-point rounding and gives rev291 a conservative multiplicative-cost value whose logarithm can be charged by the existing recurrence validator.

## Parallel retreat history

The earlier rev292 attempt was closed unmerged after a naturally triggered runner exposed a separately owned pre-existing rev292 handoff-composition branch that had not appeared in the pre-claim branch search. A later rev294 attempt was also closed unmerged when another owner created a rev294 signed-ground proof-DAG branch after this session had claimed rev294. Both own branches were left untouched and no sibling execution was modified.

Rev320 deliberately uses a non-adjacent target revision, a fresh main-visible claim, a fresh run directory, workflow, and evidence paths. Ownership must still be rechecked before integration.

## Strict boundary

Rev320 does **not** import rev287, rev291, rev292, rev293, or rev294 branch-only modules; rerun their workflows; discover a Johnson embedding; execute recursive String Isomorphism; alter a sibling certificate; merge a sibling PR; or claim corrected Split-or-Johnson/global W1R-H6/CRX/GI/AGI closure. It is only a structural/cost adapter. State remains `NOT_AGI`.
