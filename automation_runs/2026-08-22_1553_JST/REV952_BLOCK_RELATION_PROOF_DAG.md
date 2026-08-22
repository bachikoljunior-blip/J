# AGI-GI rev952 — homogeneous block relation provenance proof-DAG admission

## Scope

This revision closes only `crx3/structural-consumers/homogeneous-block-relation-provenance-proof-dag`.

The main-integrated rev273 verifier already proves an exact supplied unary/binary homogeneous block transport: it validates the source/target partitions, block-map bijection and mapped sizes, homogeneity of every unary block and binary block pair, exact quotient-relation transport, the canonical point lift, and exact full-relation transport. Rev952 adds the missing proof-carrying execution consumer for that exact structural certificate.

Rev952 independently reruns rev273 from the explicit source and target `RelationStructure` values and the frozen certificate partitions/block map. It admits the result only when the replayed `BlockProvenanceResult` is byte-for-byte dataclass-equal to the supplied exact result. The proof identity contains the complete source/target relation transcripts, source/target partitions, block map, canonical point lift, source/target quotient structures, original root, relation counts, and a conservative explicit verification-work charge.

## Accounting

The local terminal charge conservatively covers partition validation, every unary fibre, every binary block-pair fibre, quotient transport, canonical point-lift construction, and full-relation transport comparison. A second conservative replay charge is supplied to the shared `validate_execution_proof_dag` verifier. Both charges are finite, nonnegative, rooted at the original domain, and do not treat deterministic replay as free.

## Fail-closed boundary

Nonexact rev273 results, missing certificates, source/target domain drift, malformed or unsupported relation transcripts, exact-result tampering, certificate/point-lift/quotient drift, invalid original roots, proof payload tampering, recurrence payload tampering, and proof-DAG envelope rejection all remain noncertified.

## Parallel safety

The implementation is additive and restricted to the six paths reserved by durable claim `chatgpt-session-j-rev952-block-relation-proof-dag-20260822T1553JST-d2f7d996`. It does not modify rev1200 quotient String-Isomorphism, rev278 quotient preimage, rev276 relation/action compatibility, rev275 kernel factorization, rev274 action provenance, rev950 block-action-kernel proof-DAG, corrected Split-or-Johnson work, shared proof-DAG/recurrence/coordination implementation, `MAIN.md`, or any sibling claim/branch/PR/workflow.

## Strict remaining boundary

Rev952 proves only replay-stable structural provenance and its execution accounting. It does not discover a block system, solve quotient String Isomorphism, enumerate or recognize a quotient image group, combine relation provenance with action provenance, lift a quotient transporter to the original domain, solve nonhomogeneous fibres, close CRX1/CRX2/CRX3 as a whole, close GI, or establish AGI. State remains `NOT_AGI`.
