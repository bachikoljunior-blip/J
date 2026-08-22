# AGI-GI rev700: recursive production provenance join

## Goal

rev700 closes one narrow compatibility gap across three already-public contracts on the corrected Split-or-Johnson larger-ground path: the rev500 caller replay envelope, the rev600 main-integrated provenance object, and the rev650 recursive producer provenance certificate. It does not replace or modify any of those producers. It verifies their compact public identities are one coherent recursive result/accounting chain.

The implementation is stdlib-only and file-disjoint from all sibling scopes. No rev500, rev600, or rev650 branch-only implementation is imported.

## Exact join

The rev500 envelope digest is independently replayed from its public canonical payload and must be `mode == larger_ground_recursive`. The rev600 provenance digest is independently replayed from its public canonical payload, including its exact five verified identity artifacts in canonical field order. Because the compact rev600 output cannot itself reproduce the Git ancestry/blob checks that created it, rev700 additionally requires a literal `main_provenance_replay_verified == True` gate. Likewise, the compact rev650 certificate intentionally omits upstream parent/child measures needed to recompute its own producer digest, so rev700 requires a literal `recursive_provenance_replay_verified == True` gate rather than pretending to reconstruct evidence it does not have.

After those replay gates, rev700 requires:

- the rev500, rev600, and rev650 caller-binding identities to be identical;
- the rev600 envelope identity to equal the exact rev500 envelope identity;
- the rev500 result status to equal the rev650 exact recursive result status;
- rev600 main-integrated original-instance, transition, and result identities to equal the corresponding rev500 envelope identities;
- rev500 `result_identity` and rev600 `branch_certificate_identity` to equal the bare SHA-256 form of rev650 `result_lift_digest`;
- rev600 `branch_accounting_identity` to equal the bare SHA-256 form of rev650 `accounting_binding_digest`.

A successful join emits a deterministic `sha256:` production provenance identity over the main commit, caller/envelope identities, rev600 provenance identity, rev650 provenance identity, exact result status, and rev650 result/accounting/reduction/child-result identities.

## Fail-closed boundary

rev700 does not execute recursive String Isomorphism, rerun the Johnson reduction, authenticate Git ancestry or repository blobs itself, infer that any sibling PR is merged, convert accounting units, or claim a semantic theorem from identity equality alone. rev600 remains the owner of Git/main provenance; rev650 remains the owner of recursive producer-to-caller compatibility; rev620 remains an unrelated small-order production proof-DAG scope. A rev700 certificate only states that replay-verified instances of those public contracts agree exactly on the recursive production identity chain.

This leaf does not change `agi_state`; the repository remains `NOT_AGI`.
