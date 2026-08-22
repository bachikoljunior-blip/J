# rev3700 — signed Johnson ground exact-terminal public replay seal

## Scope

This revision adds one additive, read-only public replay layer above the already-main-integrated rev295 signed-Johnson-ground exact-terminal proof-DAG consumer.

It does not modify rev176, rev220, rev289, rev295, shared recurrence/proof-DAG code, `MAIN.md`, or any sibling branch-only implementation.

## Replay contract

A seal is issued only after independently executing rev295 and obtaining its certified exact proof-DAG result. The deterministic SHA-256 payload binds:

- rev295's complete replay-stable proof identity;
- exact nonempty versus exact-empty terminal status;
- the exact nonempty right-coset representative plus frozen subgroup identity, or the literal exact-empty identity;
- original root, point-domain degree, Johnson ground/subset sizes;
- certified signed-ground group order, exact signed-element scan count, recognition work, and resource gates;
- shared proof-DAG status, occurrence metrics, finite work bound, and allowed envelope;
- the mechanically derived rev176 local cost bound.

`verify_signed_johnson_ground_public_replay_seal` first validates the closed seal shape and arithmetic invariants, then independently reruns rev295 from the supplied group, strings, root, and resource/envelope gates and requires exact dataclass equality with the rebuilt seal.

## Fail-closed boundary

No seal is issued for nonexact rev176/rev295 outcomes, resource-cap exhaustion, opaque identities, non-finite accounting, proof-DAG envelope rejection, malformed result shape, scan-count drift, or group-order gate drift. Any seal mutation or supplied input/resource change is rejected on replay.

## Parallel boundary

The implementation imports only main-integrated rev295 and legacy dependencies already used by rev295. It is file-disjoint from the active rev3600 homogeneous-block replay-coherence lane and all corrected Split-or-Johnson, quotient/original-domain, relation-twin, and repository-coordination scopes.

## Non-claims

This is an integrity/replay layer over an already exact bounded signed-Johnson-ground terminal. It does not solve the larger signed-ground recursive case, corrected Split-or-Johnson, CRX3, Graph Isomorphism, or AGI. Repository state remains `NOT_AGI`.
