# AGI-GI rev1800 — homogeneous-block quotient String-Isomorphism proof-DAG boundary

## Scope

Durable claim: `chatgpt-session-j-rev1800-homogeneous-block-quotient-si-proof-dag-20260822T165100JST-293414fa`.

This revision owns only `crx3/algorithmic-consumers/homogeneous-block-quotient-string-isomorphism-proof-dag`. It is a post-replay proof-carrying consumer for the public field/status contract exposed by rev1200 / PR #260. It does not import that branch-only implementation and does not alter rev1200, rev278, rev276, rev1600, corrected Split-or-Johnson work, `MAIN.md`, or shared accounting code.

## Exact boundary

The consumer accepts only rev1200's exact-complete outcomes: nonempty quotient right coset, exact-empty feature-inventory mismatch, or exact-empty completed partition orbit. An undetermined resource-cap outcome, malformed public result, drifted digest, nonexact certificate, mismatched result snapshot, or failed upstream replay is rejected fail-closed.

For each admitted result it independently replays from main-integrated contracts:

- rev274 block-system action equivariance and paired quotient generators;
- rev275 exact kernel/image factorization;
- rev950 block-action kernel proof-DAG certification;
- the quotient feature-inventory pullback through the certified block bijection;
- the bounded complete ordered feature-partition orbit in the certified source quotient image;
- nonempty cross-coordinate quotient representative construction and target feature-stabilizer conjugation.

The frozen identity contains source/target quotient feature strings, rev274/rev275 digests, root/domain measures, the explicit partition-state cap, complete exact public-result snapshot, and the main-integrated rev950 proof identity. The result is a terminal recurrence leaf at the quotient-block degree and is occurrence-charged by the shared execution proof-DAG with a conservative state-cap-based local bound plus upstream/replay work.

## Non-claims

The quotient representative returned by rev1200 is cross-coordinate: it is not asserted to lie directly in either side's quotient image. Consequently rev1800 does **not** pass that representative to rev278's one-side preimage primitive and does not manufacture an original-domain transporter. Original-domain quotient preimage/lift remains the independently owned rev278 / PR #222 boundary.

This revision also does not combine rev273 relation provenance with rev274 action provenance, execute a corrected Split-or-Johnson recursive child, close CRX3 globally, prove full Graph Isomorphism, or establish AGI.

## Validation plan

The dedicated workflow compiles the module/tests, reruns main-integrated rev950 regressions, runs focused exact-nonempty/exact-empty/fail-closed rev1800 regressions, rejects branch-only rev1200/rev278 imports and original-domain lifting, previews canonical `attempt_solution` and `publish` admissions from the current main registry, and enforces the claim's additive reserved diff.

Because rev1200 / PR #260 remains independently owned, open, draft, and unmerged, rev1800 is draft-only even if its exact-head CI becomes green. `agi_state` remains `NOT_AGI`.
