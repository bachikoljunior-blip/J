# Rev320 — Johnson construction cost binding

## Scope

This revision is the collision-resistant re-scope of the earlier superseded rev292/rev294 cost-binding attempts. It closes one accounting interface between two separately owned corrected Split-or-Johnson leaves without modifying either sibling implementation.

- rev287 constructs and certifies the exact `J(v,k) -> v` relational reduction and retains `construction_work_bound` together with canonical Johnson incidence data and induced ground generators.
- rev291 consumes a relational-reduction-shaped object and charges `log2(max_multiplicative_cost)` before admitting the `C(v,k) -> v` auxiliary shrink into main recurrence accounting.
- rev320 requires the caller to have mechanically replayed rev287 against its original embedding and ambient generators, validates every retained rev287 field that can be reconstructed independently, and binds deterministic construction work into a conservative rev291-compatible multiplicative cost.

The explicit replay gate is necessary because rev287's `reduction_identity` commits to original ambient generators that are not themselves retained in the result object. Rev320 therefore does not accept a detached structurally plausible object merely because it carries a SHA-256-shaped identity.

The source `reduction_identity` is preserved unchanged. A separate `cost_binding_identity` commits to the replay gate, source identity, retained dimensions/work, and output cost bound.

## Fail-closed checks

The adapter rejects a missing/false/non-boolean rev287 replay gate, malformed schema/status/certification flags, malformed Johnson parameters, failure of `C(v,k) -> v` progress, any schema-v1 source cost other than rev287's exact `1.0/1.0`, non-SHA256 reduction identities, incomplete or noncanonical Johnson vertex subsets, incidence stars inconsistent with the retained canonical subsets, invalid induced ground permutations, and any mismatch between `construction_work_bound` and rev287's retained formula

`(2 + 2*g) * C(v,k) * k + g * C(v,k) + v`,

where `g` is the number of retained induced ground generators.

The finite handoff cost is the next power of two at least as large as the deterministic construction-work bound (and, mechanically, at least the exact source upper bound). This avoids downward floating-point rounding and gives rev291 a conservative multiplicative-cost value whose logarithm can be charged by the existing recurrence validator.

## Parallel retreat history

The earlier rev292 attempt was closed unmerged after a naturally triggered runner exposed a separately owned pre-existing rev292 handoff-composition branch that had not appeared in the pre-claim branch search. A later rev294 attempt was also closed unmerged when another owner created a rev294 signed-ground proof-DAG branch after this session had claimed rev294. Both own branches were left untouched and no sibling execution was modified.

The first rev320 admission preview exposed a lifecycle bug in this session's own earlier records: their descriptive status strings began with `superseded_...` but `automation/parallel_claims.py` only treats exact closed-state tokens such as `superseded` as closed. The session corrected only its own rev292/rev294 claim records on main to canonical `status: superseded` plus `completed_at_jst`, then carried the identical closed records into the rev320 branch snapshot. No sibling claim was edited.

Rev320 deliberately uses a non-adjacent target revision, a fresh main-visible claim, a fresh run directory, workflow, and evidence paths. Its dedicated workflow invokes the repository's canonical phase-admission generator on the exact PR head and prints the replayable attempt-solution payload; the payload is persisted only after the generator itself admits the phase.

## Strict boundary

Rev320 does **not** import rev287, rev291, rev292, rev293, or rev294 branch-only modules; fabricate source replay; rerun sibling workflows; discover a Johnson embedding; execute recursive String Isomorphism; alter a sibling certificate; merge a sibling PR; or claim corrected Split-or-Johnson/global W1R-H6/CRX/GI/AGI closure. It is only a structural/cost adapter. State remains `NOT_AGI`.
