# Rev3600 homogeneous-block public replay joint coherence

## Scope

This additive leaf binds two independently replay-verified public snapshots without importing either upstream branch-only implementation:

1. the main-integrated rev3300 block-action-kernel replay seal; and
2. the independently owned rev3500 relation-provenance replay seal.

It does not re-execute either upstream proof. Instead, each caller must supply a strict closed public view with a literal replay gate. The leaf requires one common original-root identity, domain degree, block count, and block size; rejects arithmetic or schema drift; preserves relation-side `ok` versus `exact_empty`; requires distinct upstream public seals; and domain-separates the complete accepted tuple into one deterministic SHA-256 coherence identity.

## Fail-closed boundary

Unknown fields, coercible booleans/integers, malformed digests, replay gates that are not literal true, unsupported status values, block arithmetic mismatch, shared-domain drift, identical upstream seal identities, certificate mutation, or certificate schema drift are rejected.

The certificate does not establish quotient String-Isomorphism, original-domain lifting, semantic equivalence beyond the explicitly shared tuple, CRX3, Graph Isomorphism, or AGI. `agi_state` remains `NOT_AGI`.

## Parallel boundary

Only the six paths reserved by claim `chatgpt-session-j-rev3600-homogeneous-block-public-replay-joint-coherence-20260822T210300JST-2a893a3e` are in scope. rev3500, rev3400, rev3300 source paths, corrected Split-or-Johnson branches, homogeneous-block quotient/original-domain branches, `MAIN.md`, shared proof-DAG/recurrence/S1/coordination implementations, sibling claims, PRs, branches, and workflows are excluded.

The PR must remain draft and unmerged while rev3500 is independently owned or unmerged. No sibling workflow is to be cancelled or manually rerun, and no sibling branch is to be rebased, force-pushed, overwritten, closed, or merged by this scope.

## Validation

The implementation passed `py_compile` and all 16 standard-library focused regressions. The dedicated GitHub workflow repeats compile/regression checks, rejects branch-only dependency strings, generates canonical `attempt_solution` and `publish` admission previews from the repository admission generator, enforces the reserved-path diff, and persists the two reserved evidence records only once on the source branch.

The independently owned current-registry hardening series has now merged. Under that hardened contract, a natural rev3600 run persisted both canonical phase records at bot commit `6fe9222e00b66d9c79ef41095b253c9d991fc6e6`. Both phases record `admitted=true`, `mode=exclusive`, `conflicts=[]`, `registry_source_sha=d1166dba0fafa40c29c2d9d79a3aab3a68f5ba3b`, and registry digest `sha256:4f2ef3dced57e7ec51c32ad93a966c9c12bc8a3db6e84a97a451b80818e52728`.

The evidence-producing implementation head `d9efe2ba2f25bac4d433ab0a48e193f2faeca731` passed the dedicated rev3600 smoke naturally. This connector-authored reserved documentation heartbeat follows the bot evidence commit so ordinary PR checks can evaluate an evidence-bearing exact head without any manual workflow rerun.
