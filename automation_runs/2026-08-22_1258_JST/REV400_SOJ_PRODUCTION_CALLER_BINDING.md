# AGI-GI rev400 — corrected Split-or-Johnson production caller binding

## Scope

This revision addresses one remaining caller-boundary leaf under W1R-H6: bind one and only one already-certified corrected Split-or-Johnson result path into a deterministic production-caller evidence object without silently crossing identities or accounting records.

The accepted alternatives are deliberately exclusive:

1. a small-ground exact terminal with its terminal accounting record; or
2. a larger-ground exact recursive result with its recursive-result accounting binding.

The binder requires literal boolean `canonical`/`exact` flags, lowercase 64-hex identities, exact transition and original-instance identity agreement, exact result/status agreement, and nonnegative integer work accounting. It rejects both branches, neither branch, mode drift, transport/original-instance drift, result/accounting drift, malformed identities, implicit boolean/integer coercions, unresolved statuses, and unsupported root or selected-branch fields. Rejecting unknown fields prevents shadow/override data from crossing the production caller boundary without participating in the deterministic binding identity. Its output is normalized to a fixed schema and receives a deterministic SHA-256 `caller_binding_identity`.

## Relationship to concurrent corrected-SOJ work

This revision is intentionally a sibling of the existing recurrence, terminal, larger-ground reduction/handoff, normalization, proof-DAG, construction-cost, recursive-result-lift, and recursive-result-accounting efforts. It does not modify or supersede those claims, branches, PRs, reserved paths, or workflows. In particular, it does not duplicate the mathematical work owned by rev283, rev284, rev285, rev286, rev287, rev288, rev289, rev290, rev291, rev292, rev293, rev295, rev320, or rev340.

Instead, the module is a narrow fail-closed interface that can consume snapshots only after their producing layers have independently replayed and verified them. This closes the previously explicit gap where caller wiring was left outside those revisions.

## Trust boundary

The module is **not** a String-Isomorphism solver. It does not construct a Johnson reduction, perform recursive SI, verify group-theoretic semantics, authenticate a SHA-looking identity, prove that a supplied certificate is mathematically true, or establish the complexity bound of a producer. Those responsibilities remain with the producer/replay layers whose identities are being bound.

Consequently, passing this binder is not evidence that corrected Split-or-Johnson is globally closed. It is not evidence of GI or AGI completion, and this revision remains `NOT_AGI`.

## Verification

The focused regression suite contains valid exact-empty and exact-nonempty cases for both alternatives plus fail-closed checks for mutual exclusivity, mode mismatch, transition/original/result/accounting drift, malformed SHA identities, nonliteral boolean evidence, noninteger/negative accounting, unresolved status, unsupported shadow fields at the root and selected branch, deterministic replay, and tamper-sensitive binding identity.

Before publication, the branch must also satisfy repository parallel-admission requirements. No phase-admission JSON is fabricated by this revision: if the repository replay gate cannot verify a real admission record from the exact registry source, the PR must remain unmerged.
