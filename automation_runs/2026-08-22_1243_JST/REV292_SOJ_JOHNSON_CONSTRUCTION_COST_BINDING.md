# Rev292 — Johnson construction cost binding

## Scope

This revision closes one accounting interface between two separately owned corrected Split-or-Johnson leaves without modifying either sibling implementation.

- rev287 constructs and certifies the exact `J(v,k) -> v` relational reduction and retains `construction_work_bound` together with the canonical Johnson incidence data and induced ground generators.
- rev291 consumes a relational-reduction-shaped object and charges `log2(max_multiplicative_cost)` before admitting the `C(v,k) -> v` auxiliary shrink into main recurrence accounting.
- rev292 validates the retained rev287 certificate structure and its exact deterministic work formula, then replaces a potentially unit source cost with a conservative finite power-of-two upper bound at least as large as both the retained construction work and the source cost bound.

The source `reduction_identity` is preserved unchanged. A separate `cost_binding_identity` commits to the cost-binding inputs and output bound.

## Fail-closed checks

The adapter rejects malformed schema/status/certification flags, malformed Johnson parameters, failure of `C(v,k) -> v` progress, invalid source cost bounds, non-SHA256 reduction identities, incomplete or noncanonical Johnson vertex subsets, incidence stars inconsistent with the retained canonical subsets, invalid induced ground permutations, and any mismatch between `construction_work_bound` and rev287's retained formula

`(2 + 2*g) * C(v,k) * k + g * C(v,k) + v`,

where `g` is the number of retained induced ground generators.

The finite handoff cost is the larger of the source upper bound and the next power of two above the deterministic construction-work bound. This avoids a downward floating-point rounding issue and gives rev291 a conservative multiplicative-cost value whose logarithm can be charged by the existing recurrence validator.

## Strict boundary

Rev292 does **not** import rev287 or rev291 branch-only modules, rerun the rev287 construction, discover a Johnson embedding, execute recursive String Isomorphism, alter a sibling certificate, merge a sibling PR, or claim corrected Split-or-Johnson/global W1R-H6/CRX/GI/AGI closure. It is only a structural/cost adapter. State remains `NOT_AGI`.
