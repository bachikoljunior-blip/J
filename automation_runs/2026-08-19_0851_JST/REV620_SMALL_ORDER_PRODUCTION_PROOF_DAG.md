# rev620 — proof-carrying small-order production proof-DAG consumer

## Scope

rev620 is a CRX3 algorithmic consumer. It does not change the shared String-Isomorphism solver, rev252 production admission, the shared proof-DAG implementation, corrected Split-or-Johnson, CRX1/CRX2, or `MAIN.md`.

It composes two main-integrated proof boundaries:

- rev252 `proof_carrying_small_order_production_admission_v1`, which preflights the finite work, checks the exact producer proof/recurrence leaf, independently enumerates the represented Schreier group, builds a deterministic replay certificate, and exhaustively replays the claimed exact match set; and
- rev220/rev289 `proof_dag_accounting_v1`, which requires a replay-stable execution identity and charges every execution occurrence conservatively.

## Exact admission contract

The consumer snapshots source/target values before execution and fails closed for unsupported/opaque values. It then performs the rev252 preflight, executes the already-main-integrated small-order exact producer once, and runs rev252's independent production-result verifier against that exact producer.

Only `ADMITTED_EXACT` outcomes with `VERIFIED_EXACT` replay can receive a proof-DAG identity. The identity freezes:

- the represented Schreier group;
- full oriented source and target strings;
- original root and current degree;
- certified group order and exact producer scan count;
- exact nonempty versus exact-empty terminal status;
- rev252 claimed-match count, replay certificate SHA-256, recurrence status, replayed group/action measures, and target-stabilizer size;
- every production/replay resource gate; and
- a conservative external log2 charge for the independent rev252 enumeration/certificate/replay work.

The underlying producer's recurrence leaf remains unchanged. The independent rev252 verification work is supplied to the shared proof-DAG validator through its external-cost channel rather than being silently omitted.

## Fail-closed cases

No proof-DAG certification is produced for resource-cap outcomes, unsupported input snapshots, nonexact producer/admission/replay states, identity or certificate drift, inconsistent group/scan/replay fields, malformed exact cosets, accounting drift, non-finite envelope inputs, or shared proof-DAG rejection.

## Parallel boundary

rev620 writes only its dedicated consumer, regression, memo, smoke workflow, and canonical phase-admission evidence. It imports only main-integrated substrates. It does not import sibling branch-only corrected-SOJ, block-kernel, primitive-Johnson proof-DAG, literal-giant, parent-outcome, or other concurrent modules.

## AGI state

`NOT_AGI`. rev620 certifies one already-bounded exact small-order production terminal as a reusable proof-DAG node. It does not close larger-group structural recursion, corrected Split-or-Johnson production wiring, GI, or AGI.
