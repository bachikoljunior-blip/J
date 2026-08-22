# AGI-GI rev2500 — parent-filtered result / execution proof-DAG binding

## Scope

This leaf binds two independently owned corrected Split-or-Johnson public certificates without importing their branch-only implementations:

- rev2200: an exact parent-filtered result obtained by replaying the induced-ground child transporter set and filtering every candidate against the full parent Johnson string;
- rev1400: a recursive-production execution proof-DAG certificate whose proof identity commits to one concrete proof-carrying child execution.

The adapter certifies only that both certificates refer to the same reduction, the same exact child-result identity, and the same child action degree. It deliberately does **not** identify the two independently defined parent-result certificates.

## Replay checks

The rev2200 certificate is replayed from its public result payload, including exact/canonical coset shape and `result_identity`. The rev1400 certificate is checked for exact/certified status, strict parent-to-child shrink, closure/result-lift/child-result links inside its replay-stable proof identity, and replay-stable child proof identity.

Cross-certificate binding requires equal `reduction_identity`, equal `child_result_identity`, and rev2200 `action_degree == rev1400.child_ground_size`.

An exact-empty rev1400 child execution can only bind to a zero-candidate exact-empty rev2200 result. A nonempty child execution may still bind to an exact-empty rev2200 parent result because rev2200 intentionally removes projection false positives by checking the full parent Johnson string.

## Fail-closed boundary

The adapter rejects malformed hashes, result-identity drift, inconsistent exact-empty/nonempty shapes, opaque proof identities, unstable child proof identities, action-degree drift, reduction drift, and child-result drift.

`same_child_execution_certified=true` means shared child execution lineage only. `parent_result_identity_equivalence_certified` is hard-coded to `false`: rev2500 does not claim that rev1400's parent lift and rev2200's parent-filtered certificate are the same parent certificate.

rev2500 also does not construct the parent→child semantic reduction, does not perform recurrence accounting, does not import or alter rev2200/rev1400, and does not close corrected Split-or-Johnson/GI. AGI state remains `NOT_AGI`.

## Validation

The focused suite covers nonempty binding, projection-false-positive filtering, exact-empty implication, result/digest tampering, reduction and child-result mismatch, action-degree mismatch, unstable proof identity, malformed parent coset shape, and deterministic replay.

## Canonical phase-evidence recovery

The first repository-wide parallel-admission check failed closed only because this branch did not yet contain its two reserved phase-admission evidence files. The dedicated workflow had already passed its focused tests and canonical admission previews, but the initial source-branch materialization raced with the then-concurrent rev2500 target-revision collision that was later resolved by the other scope moving to rev2707. This documentation-only commit intentionally triggers a new natural run of this claim's own dedicated workflow; that workflow may materialize only the already-reserved `attempt_solution` and `publish` evidence paths. No sibling claim, branch, PR, workflow, or run is modified, cancelled, or manually rerun.
