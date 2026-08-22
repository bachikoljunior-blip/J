# rev3300 — homogeneous block-action kernel-factorization public replay seal

## Scope

This revision adds one additive, read-only consumer above the already-main-integrated rev950 proof-DAG terminal for rev275 homogeneous block-action kernel factorization.

Given explicit rev274 provenance and rev275 factorization evidence, rev3300 re-executes the main-integrated rev950 consumer and accepts only its certified exact canonical terminal. It then freezes the replay-stable proof identity into one domain-separated deterministic SHA-256 seal covering:

- rev274 provenance and rev275 factorization digests;
- original-root, domain degree, block count, and generator count;
- rev275 work-cap / estimated Schreier-work / sift-level identity;
- source/target group, common quotient-image, and source/target kernel orders, including both `|G| = |ker| |im|` equalities;
- independent digests of the source and target kernel-generator families;
- the complete rev950 proof identity;
- shared execution proof-DAG status, occurrence metrics, and finite work/envelope bounds;
- rev950's finite external replay charge.

`verify_block_action_kernel_public_replay_seal` first checks the public seal's own shape and arithmetic invariants, then independently re-executes rev950 from the supplied provenance/factorization inputs and requires byte-for-byte dataclass equality with the rebuilt seal.

## Fail-closed boundary

No seal is issued for nonexact/incomplete rev275 evidence, failed rev275 replay, malformed provenance/factorization digests, root/domain drift, work-cap violations, order-factorization drift, malformed kernel permutations, non-finite accounting, or a shared proof-DAG envelope failure. Any seal mutation or any supplied-input drift causes verification to fail closed.

## Parallel boundary

rev3300 changes only its six reserved additive paths. It does not modify rev274, rev275, rev950, shared proof-DAG/recurrence code, `MAIN.md`, corrected Split-or-Johnson code, homogeneous-block quotient/original-domain lifting code, relation-twin code, coordination implementations, or any sibling claim/branch/PR/workflow.

The implementation imports only main-integrated rev950 and legacy dependencies already used by rev950; it does not import sibling branch-only implementations.

## Non-claims

A public replay seal is an identity/integrity layer over an already-certified exact structural factorization. It does **not** solve quotient String Isomorphism, intersect a quotient result with an original-domain parent coset, prove a complete corrected Split-or-Johnson recursion, or establish CRX3, GI, or AGI. Repository state therefore remains `NOT_AGI`.
