# Rev360 — Johnson construction cost binding

## Scope

Rev360 is a fresh-main, collision-resistant re-scope of the earlier rev292/rev294/rev320 attempts. It closes one accounting interface between separately owned corrected Split-or-Johnson leaves without modifying them.

- rev287 retains an exact/canonical `J(v,k) -> v` relational-reduction certificate plus deterministic `construction_work_bound`.
- rev291 charges `log2(max_multiplicative_cost)` before admitting the `C(v,k) -> v` auxiliary shrink into recurrence accounting.
- rev360 requires mechanical rev287 replay against the original embedding/ambient generators, revalidates the retained Johnson incidence data and deterministic work formula, and replaces rev287 schema-v1's unit cost with a conservative finite power-of-two upper bound suitable for rev291 accounting.

The replay gate is necessary because rev287's `reduction_identity` commits to original ambient generators that are not retained in the detached result object. A SHA-256-shaped string alone is not treated as authenticity evidence.

## Fail-closed checks

The adapter rejects a missing/false/non-boolean source replay gate; malformed schema/status/certification flags; malformed Johnson parameters; failure of `C(v,k) -> v` progress; source costs other than rev287 schema-v1's exact `1.0/1.0`; malformed reduction identity; incomplete/noncanonical `k`-subset families; inconsistent canonical ground stars; non-permutation induced ground generators; and any mismatch with rev287's retained formula

`(2 + 2*g) * C(v,k) * k + g * C(v,k) + v`.

The output cost is the next power of two at least the deterministic construction-work count. The original `reduction_identity` is preserved and a separate `cost_binding_identity` commits to the replay gate, source identity, dimensions, work count, and output bound.

## Parallel history

This session's earlier rev292 and rev294 PRs were closed unmerged on target-revision collisions. Rev320 then exposed that the session's own descriptive `superseded_...` claim statuses were not canonical closed states; those own records, plus rev320, are now canonically closed on main with exact `status: superseded` and `completed_at_jst`. No sibling claim was edited. Rev360 was claimed only after a fresh search showed no rev360 branch and starts from main containing those closures.

The dedicated workflow runs compilation, 14 focused regressions, reserved-path enforcement, and the repository's canonical `attempt_solution` generator. It prints a mechanically generated evidence payload only if admission succeeds; no admission evidence is hand-authored.

## Strict boundary

Rev360 does not import or modify sibling branch-only implementations, fabricate rev287 replay, discover a Johnson embedding, execute recursive String Isomorphism, alter sibling certificates, merge/rerun sibling PRs or workflows, or claim corrected Split-or-Johnson / W1R-H6 / CRX / GI / AGI closure. State remains `NOT_AGI`.
