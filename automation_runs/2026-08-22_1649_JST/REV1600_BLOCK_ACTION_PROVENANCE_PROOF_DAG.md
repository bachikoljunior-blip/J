# rev1600 — homogeneous block-action provenance proof-DAG admission

Scope: `crx3/structural-consumers/homogeneous-block-action-provenance-proof-dag`.

This revision attaches only the already-main-integrated rev274 `BlockActionProvenance`
contract to the shared conservative execution proof-DAG. It does not discover a block
system, solve quotient String-Isomorphism, factor a kernel, lift a quotient transporter,
or combine independently owned relation/action certificates.

The consumer independently replays rev274 and freezes the canonical source/target block
partitions, block bijection, paired original-domain generators, paired quotient generators,
exact intertwining transcript, deterministic certificate digest, original root, and a
finite conservative replay/work charge into one immutable proof identity. Exact/complete
rev274 evidence is required. Any replay drift, malformed digest/permutation, root drift,
accounting drift, or proof-DAG envelope failure remains fail-closed.

Parallel boundary: rev950 kernel-factorization proof-DAG, rev952 relation-provenance
proof-DAG, rev1200 quotient SI, rev278 quotient preimage, rev276 relation/action
compatibility, corrected Split-or-Johnson work, CRX1/CRX2, shared proof-DAG/recurrence
implementation, `MAIN.md`, sibling claims/branches/PRs/workflows are read-only.

This is a structural consumer leaf only. It does not close CRX3, Graph Isomorphism, or
AGI. Repository state remains `NOT_AGI`.
