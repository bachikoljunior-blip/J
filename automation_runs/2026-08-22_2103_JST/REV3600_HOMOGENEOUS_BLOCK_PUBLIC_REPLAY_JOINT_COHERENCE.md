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

Before publication, the module and tests were independently materialized in a clean local temporary directory: `py_compile` succeeded and all 16 standard-library focused regressions passed. The dedicated GitHub workflow repeats compile/regression checks, rejects branch-only dependency strings, previews canonical `attempt_solution` and `publish` admission against the claim-aligned main source, and enforces the reserved-path diff.
