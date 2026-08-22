# Rev2501 relation-twin restriction replay identity

This revision closes one narrow structural-reuse gap around the main-integrated rev203 paired relation-twin restriction. It does not change rev203 or rev200 and does not promote a local restriction to a complete parent String Isomorphism result.

The new consumer normalizes the declared bipartite source and target edge sets, `alpha`, and `max_subsets`; records both exact relation-twin partitions, the unique over-half twin classes, complements, and the selected rev200 proper restrictions; and hashes the full semantic payload with SHA-256. Validation independently reruns `certify_paired_relation_twin_restriction` and requires the supplied result, the rebuilt structural snapshot, the resource identity, and the digest to agree exactly.

Only `paired_relation_twin_restriction` outcomes with exact paired provenance, complete restriction pairing, exact rev200 certificates, and verified theorem gates receive a reusable identity. No-large-class outcomes, source/target status or inventory mismatches, resource drift, input drift, digest tampering, or structural replay drift remain fail-closed.

The scope is deliberately additive and disjoint from active corrected Split-or-Johnson and homogeneous-block work. It imports only the public main-integrated rev203/rev200 implementation from `automation_runs/2026-08-19_0851_JST`; it does not import sibling branch-only modules, alter shared proof-DAG or recurrence code, or touch another session's branch, PR, claim, or workflow.

AGI state remains `NOT_AGI`. CRX3, general GI, parent exact-set reconstruction, and global quasipolynomial closure remain unresolved.
