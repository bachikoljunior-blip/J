# rev290 — strict normalized Johnson cost binding

## Scope

This leaf binds two already-owned corrected Split-or-Johnson certificates without importing either branch-only implementation:

- rev288 strict normalized Johnson transition/terminal evidence; and
- rev286 corrected-SOJ Johnson terminal-cost accounting.

The binding is intentionally post-replay. The caller must first replay each sibling certificate with its owning implementation, then pass exact boolean replay results. rev290 independently checks that both certificates refer to the same root envelope, current domain, transition fields, terminal fields, and terminal recurrence leaf.

## Exact boundary

The binder rejects coercible replay flags, non-finite charges, malformed SHA-256 identities, transition or terminal field drift, root/measure drift, non-terminal accounting children, uncertified accounting, and disagreement between the composed accounting charge and the transition plus terminal charges. On success it emits a deterministic SHA-256 identity over both sibling proof identities and the shared accounting envelope.

This closes a cross-certificate/TOCTOU gap only. It does not admit or execute corrected-SOJ, execute primitive Johnson, prove the transition or terminal cost bounds, promote a coset, perform production routing, modify recurrence implementations, or claim GI/AGI completion.

## Parallel safety

The implementation imports standard-library modules only. rev275 takeover, rev276-rev289 branches/claims/PRs/workflows, PR #226, PR #228, PR #229, PR #230, PR #231, PR #232, rev291 larger-ground Johnson handoff, CRX1/CRX2/CRX3 implementation paths, proof-DAG paths, `MAIN.md`, and shared coordination implementation are read-only/excluded.

## Validation state

The first dedicated rev290 smoke completed successfully with compile, all 11 focused regressions, and the reserved-diff gate green. The dedicated smoke then materialized the canonical `attempt_solution` phase-admission evidence on the rev290 branch using the repository admission generator; that evidence records `admitted=true`, no conflicts, and an exact registry source SHA. A follow-up connector-authored commit intentionally touches only this reserved document so the PR checks run again against a head that already contains the replayable admission evidence.

rev290 remains a draft dependency adapter until the owning rev288 and rev286 contracts are integrated in dependency order. No sibling branch, claim, PR, or workflow is modified or rerun.

AGI state remains `NOT_AGI`.
