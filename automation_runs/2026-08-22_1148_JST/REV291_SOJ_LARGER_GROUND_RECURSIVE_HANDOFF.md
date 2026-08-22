# Rev291 — larger-ground Johnson recursive handoff

## Scope

This revision fills only the file-disjoint handoff boundary left open by the corrected Split-or-Johnson Johnson terminal slices. The main-integrated primitive Johnson terminal deliberately returns `undetermined_johnson_ground_cap` when a certified `J(v,k)` ground is outside the explicit/polylog brute-force window. Rev291 does not relabel that result as exact and does not invent the missing relational reduction.

Instead, `corrected_soj_larger_ground_recursive_handoff_v1.py` admits a recursive handoff only when caller-supplied reduction evidence is already canonical, exact, progress-certified, solution-transport certified, ambient-membership-transport certified, and explicit about Johnson complement ambiguity. It independently binds the recognized Johnson dimensions to the represented action degree by checking `C(v,k) == domain_size`, binds the child auxiliary measure to the certified ground `v`, requires a canonical SHA-256 reduction identity and an externally certified multiplicative cost bound, and then asks the main `quasipoly_recurrence_accounting_v1` validator to accept the `C(v,k) -> v` edge as an `aux_shrink` step.

## Fail-closed boundaries

Rev291 intentionally does **not** construct the Johnson-ground relational instance, prove the exact solution-transport theorem, derive an ambient group on the ground, manufacture a reduction cost certificate, import branch-only rev281/rev283/rev284/rev286/rev288/rev290 code, or claim full corrected Split-or-Johnson closure. Those remain separate proof obligations. Any missing/malformed/coercible evidence, dimension mismatch, non-finite or underbounded cost, noncanonical identity, child-measure mismatch, insufficient shrink, or recurrence rejection leaves the handoff uncertified.

## Verification

The focused regression contains 17 tests covering the certified replayable path plus ground-cap status/canonicality, exactness laundering, binomial action-degree reconstruction, strict booleans, reduction exactness/canonicality/progress, solution and ambient-membership transport, complement handling, dimension binding, cost certification, canonical digest shape, child/root binding, configured shrink, main recurrence fail-closed behavior, and replay drift. Local execution before publication completed 17/17 tests successfully and `py_compile` succeeded for the rev291 implementation and test.

## Parallel safety

The rev291 branch writes only its four reserved implementation/test/documentation/workflow paths. Rev275 takeover and rev276–rev290 claims/branches/PRs/workflows/reserved paths, including PRs #226, #228, #229, #230, #231, #232 and the rev289/rev290 scopes, are read-only dependencies or explicit exclusions. `MAIN.md`, CRX scopes, state-orbit/proof-DAG scopes, sibling claims, and sibling workflows are not modified.
