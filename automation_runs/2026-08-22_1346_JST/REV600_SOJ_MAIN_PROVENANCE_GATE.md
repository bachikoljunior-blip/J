# rev600 corrected-SOJ main provenance gate

## Scope

This leaf adds a fail-closed repository-provenance layer after the public rev400 production-caller binding and rev500 replay envelope contracts. It answers only a narrow integration question: are the SHA-256 identities carried by an already replayed corrected-SOJ caller result anchored to explicit JSON evidence whose exact bytes were introduced at a stated commit, remain unchanged at the resolved `main` commit, and are reachable from that `main` commit?

It does **not** infer mathematical truth merely from main reachability, execute corrected Split-or-Johnson, run recursive String Isomorphism, prove a Johnson reduction, certify producer semantics, or promote GI/AGI status.

## Mechanical contract

`soj_main_provenance_gate_v1.py` independently reconstructs the public rev400 caller-binding digest and rev500 replay-envelope digest instead of importing their separately owned branch-only implementations. It then requires exactly one provenance requirement for each caller identity field:

- `original_instance_identity`
- `transition_identity`
- `result_identity`
- `branch_certificate_identity`
- `branch_accounting_identity`

Each requirement must provide the exact identity key, a lowercase 40-hex source commit, a canonical repository-relative POSIX JSON path, and a lowercase 64-hex SHA-256 of the source blob. The source commit must be an ancestor of the single resolved `main` commit. The source blob hash must match, the same path at resolved `main` must be byte-identical to the source blob, the blob must decode as a JSON mapping, and its named top-level identity must equal the replayed rev400 identity.

On success, rev600 seals the resolved `main` commit, rev400 caller-binding identity, rev500 envelope identity, and the five verified source tuples into a deterministic SHA-256 provenance identity. Replay recomputes every field and rejects drift.

## Fail-closed boundaries

The gate rejects malformed Git/SHA identities, nonliteral booleans, float/bool integer coercions, missing or extra identity requirements, key redirection, unsafe or traversing paths, unknown/unreachable source commits, source-content hash mismatch, later path drift on `main`, non-JSON evidence, evidence identity mismatch, rev400 binding drift, rev500 envelope drift, work-cap violations, domain/root inconsistencies, and provenance replay drift.

A passing gate means **repository content provenance only**. It does not authenticate whether a referenced mathematical certificate is true; that remains the responsibility of the producer/replay layer that generated the evidence.

## Parallel safety

The rev600 claim reserves only its dedicated workflow, note, implementation, tests, and two phase-admission snapshots. rev400 / PR #246, rev500 / PR #247, rev620 small-order proof-DAG, and rev650 larger-ground recursive caller-result provenance all remain separately owned. rev650 explicitly excludes rev600 and states that it binds recursive producer semantics without asserting main reachability; rev600 is the complementary main-reachability/content-integrity layer and does not consume or modify rev650 branch-only code.

No sibling branch, claim, PR, workflow, shared coordination implementation, `MAIN.md`, recurrence implementation, or proof-DAG implementation is modified, cancelled, rerun, rebased, force-pushed, or overwritten by this leaf.

## Validation

Before repository publication, the rev600 module and focused test file compiled successfully and all 17 focused standard-library regressions passed. Dedicated exact-head CI and canonical phase-admission evidence are required before this leaf may be considered publish-ready.

## Integration boundary

rev600 should remain draft and unmerged while the upstream rev400/rev500 production-caller/replay chain is still draft or otherwise not main-integrated. A green rev600 gate by itself does not establish corrected Split-or-Johnson, GI, or AGI. `agi_state` remains `NOT_AGI`.
