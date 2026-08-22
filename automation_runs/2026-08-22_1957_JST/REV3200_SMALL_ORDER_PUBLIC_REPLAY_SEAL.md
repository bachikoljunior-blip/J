# rev3200 — small-order production public replay seal

## Scope

This leaf consumes only the **main-integrated** rev620 proof-carrying small-order production proof-DAG consumer. It adds a compact, deterministic, re-executable public-shaped seal for downstream consumers without changing the small-order solver, rev252 admission, shared proof-DAG accounting, or recurrence implementation.

The durable claim is `chatgpt-session-j-rev3200-small-order-public-replay-seal-20260822T195700JST-cab8029f`, with scope `crx3/algorithmic-consumers/proof-carrying-small-order-production-public-replay-seal`.

## Contract

A seal is emitted only after rev620 itself returns a certified exact proof-DAG execution. The rev3200 consumer then:

1. requires exact nonempty or exact-empty small-order semantics;
2. checks the rev620 proof identity is replay-stable and agrees with the rev252 replay certificate and exact match count;
3. canonically encodes the complete rev620 proof identity with explicit type/domain separators and finite-float hexadecimal encodings;
4. separately hashes the proof identity and rev252 replay identity;
5. freezes exact outcome, root/domain/group measures, certificate digest, proof-DAG status and occurrence metrics, and conservative work/envelope bounds;
6. domain-separates that tuple into one SHA-256 `seal_sha256`;
7. exposes an independent verification entry point that re-executes rev620 from the explicit group, strings, root and resource gates and requires literal seal equality.

Exact-empty and nonempty outcomes are distinct. Resource exhaustion, nonexact rev620 evidence, malformed hashes, non-finite accounting, changed strings/resources, or any digest/accounting drift remain fail-closed.

## Parallel boundary

The implementation is additive and file-disjoint from active corrected Split-or-Johnson work through rev3100, homogeneous-block work through rev2300, relation-twin work, run-start/claim-publication coordination, `MAIN.md`, and shared solver/proof-DAG/recurrence code. It imports no sibling branch-only implementation.

The first same-session target `rev3100` was superseded before implementation when the mandatory collision recheck found an independently owned rev3100 corrected-SOJ branch. rev3200 is the collision-free replacement.

## Verification target

The dedicated smoke compiles rev3200, reruns rev620 focused regressions plus rev3200 regressions, rejects imports of active sibling branch-only implementations, previews canonical attempt/publish phase admission from the claim-publication main snapshot, and enforces the reserved-path diff.

## Strict theorem boundary

The public replay seal is an audit/reuse contract around an already-certified exact small-order terminal. It does not enlarge the class of instances solved by rev620, does not remove resource caps, does not solve corrected Split-or-Johnson or homogeneous-block quotient SI, and does not establish CRX3, Graph Isomorphism, or AGI. Repository state remains `NOT_AGI`.
