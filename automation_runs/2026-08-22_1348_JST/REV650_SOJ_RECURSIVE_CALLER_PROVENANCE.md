# AGI-GI rev650: corrected-SOJ recursive caller producer provenance binding

## Goal

rev650 closes a narrow contract gap on the larger-ground corrected Split-or-Johnson path. The public rev400 production-caller binding intentionally accepts SHA-looking producer identities after an upstream verifier has already accepted them; rev293 exposes the exact recursive parent-result transcript digest and rev340 exposes the result/accounting cross-binding digest. This leaf deterministically cross-binds those public producer digests to the recursive branch identities carried by the rev400 caller payload.

The implementation is deliberately file-disjoint and stdlib-only. It does not import any branch-only sibling module. Inputs are treated as public immutable contract snapshots plus two literal replay-verification booleans supplied by the caller.

## Required cross-binding

For `mode == larger_ground_recursive`, rev650 independently replays the public rev400 `caller_binding_identity` from the canonical JSON payload and then requires:

- a replay-verified rev293-style result-lift certificate with `certified`, `exact`, and `complete` all literal true;
- a replay-verified rev340-style accounting binding with `certified`, `exact`, and `complete` all literal true;
- exact agreement on outcome kind, parent action degree, child Johnson-ground size, reduction identity, child-result identity, and the result-lift digest referenced by accounting;
- `exact_nonempty` versus `exact_empty` agreement with the rev293 result-lift status;
- rev400 `result_identity` and `branch_certificate_identity` equal to the bare 64-hex form of the rev293 `transcript_digest`;
- rev400 `branch_accounting_identity` equal to the bare 64-hex form of the rev340 `binding_digest`.

The successful output is a deterministic `sha256:` provenance identity over the replayed rev400 caller-binding identity and the exact rev293/rev340 producer identities and shared recursive measures.

## Fail-closed boundaries

This leaf does **not** execute recursive String Isomorphism, reconstruct or replay the Johnson reduction itself, authenticate Git/GitHub reachability, or assert that any sibling branch has merged. Repository-main provenance is a separate rev600 scope, while the small-ground production proof-DAG is separately owned by rev620. rev650 also does not equate rev340's logarithmic reduction charge with rev400's integer `accounted_work`; those fields use different public accounting contracts, so silently comparing them would manufacture a unit conversion that the repository has not proved.

A successful rev650 certificate is therefore only a producer-to-caller compatibility certificate. It is not an AGI certificate and does not change the repository's `NOT_AGI` status.
