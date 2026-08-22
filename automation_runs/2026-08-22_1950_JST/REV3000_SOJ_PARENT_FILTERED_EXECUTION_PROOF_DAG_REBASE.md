# AGI-GI rev3000 — parent-filtered result / execution proof-DAG binding rebase

## Why this revision exists

The rev2500 implementation and focused tests were green, but its source branch was rooted at a registry snapshot in which a different execution still held an active rev2500 target claim. That historical sibling later failed closed and moved to rev2707, yet canonical persistent phase evidence for rev2500 must replay the immutable source-branch registry ancestry; fabricating evidence from the newer PR merge context would violate the repository evidence guard. rev3000 therefore re-homes the same narrow certificate-binding leaf on a fresh main ancestry with a distinct revision, scope and reserved paths.

No sibling claim, branch, PR, workflow or historical record is edited to make admission pass.

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

`same_child_execution_certified=true` means shared child execution lineage only. `parent_result_identity_equivalence_certified` remains hard-coded to `false`: rev3000 does not claim that rev1400's parent lift and rev2200's parent-filtered certificate are the same parent certificate.

rev3000 also does not construct the parent→child semantic reduction, does not perform recurrence accounting, does not import or alter rev2200/rev1400, and does not close corrected Split-or-Johnson/GI. AGI state remains `NOT_AGI`.

## Validation

The focused suite preserves the 12 rev2500 regression cases: nonempty binding and replay, projection false-positive filtering, exact-empty implication, result/digest tampering, reduction/child-result mismatch, action-degree mismatch, unstable proof identity, malformed parent coset shape, and deterministic binding identity. `py_compile` and all 12 focused cases passed on the first rev3000 implementation head.

The first rev3000 PR event then failed closed before evidence publication because the newly created main-side claim omitted the required `branch` field and therefore loaded as non-schema-v2. Only this session's rev3000 claim was corrected. The corrected main claim was merged normally into the isolated rev3000 branch without force-pushing or modifying any sibling resource.

After that correction, the source-branch workflow generated both reserved canonical phase-evidence files. The persisted `attempt_solution` and `publish` records each report `admitted: true`, `conflicts: []`, active ownership by this rev3000 claim, and target revision 3000. The resulting evidence commits were made by the branch's own GitHub Actions workflow. This documentation commit records that recovery and deliberately creates a normal user-authored branch update so PR workflows can validate the exact evidence-bearing head without manually rerunning or cancelling any workflow.
