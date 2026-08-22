# Current-registry replay for phase evidence

## Selected leaf

The persisted phase-admission artifact is replayed exactly at its recorded
`registry_source_sha`, but the previous guard only required that SHA to be an
ancestor of the proposed head. A later canonical-main claim could therefore
reserve the same scope, revision, or path while the older artifact remained
internally valid.

## Existing-solution audit

This change retains the repository's content-addressed source replay and Git
ancestry checks. It adds an independent admission pass against an explicitly
selected current registry ref, analogous to an up-to-date protected-branch
check. Unrelated claim heartbeats are allowed; missing or closed ownership and
new scope, revision, or reserved-path collisions fail closed.

## Implementation boundary

The pull-request workflow passes `origin/main` as the current registry ref.
The guard resolves that commit, loads its claims, chooses a deterministic
observation time covering all current claim events, and re-runs the same phase
admission. The immutable persisted snapshot must still replay exactly.

This is coordination hardening only. It does not expand the solved
String-Isomorphism instance class, does not solve GI, and does not establish
general intelligence. The forecast remains 576 problems, with 571 effective
problems; the overflow rewrite condition is not triggered. State: `NOT_AGI`.
