# AGI-GI rev252 — proof-carrying small-order production admission

## Scope

rev252 closes only the acceptance boundary for using the existing proof-carrying small-order String-Isomorphism terminal as a bounded production exact terminal. It does not alter the shared S1/U2 dispatchers or any sibling CRX1/CRX2/CRX3 branch.

The producer is the rev170 `exact_small_order_group_string_isomorphism` terminal. The independent verifier is the rev251 `exact_result_replay_verifier_v1` finite-group replay. rev252 adds a strict adapter that requires both proof systems to agree before returning `admitted_exact`.

## Admission contract

Before the producer is invoked, rev252 snapshots the source/target input and preflights every order-dependent producer/replay bound that it relies on:

- represented degree is within the production replay cap;
- Schreier-certified group order is at most both `root_n ** group_order_poly_power` and the finite production group-order cap;
- the independent group-closure replay budget includes all `|G|^2` compositions;
- the independent action replay budget includes both source/target and target-stabilizer scans, bounded by `2 * |G| * degree` point checks;
- unsupported or non-deterministically snapshotable colors fail closed before the producer executes.

An over-cap request returns `unknown_resource_cap` with `producer_invoked=False`. No structural or exact result is manufactured from a cap rejection.

## Producer proof checks

For an admitted preflight, the existing producer is executed once. rev252 then requires the returned `SmallOrderProofCarryingCoset` to be:

- canonical, exact, locally cost-certified, and terminal-certified;
- the `small_order_group_si_terminal` operation at the exact root/current degree;
- certified for the same Schreier group order as the caller's represented group;
- backed by a matching terminal recurrence-accounting leaf accepted by `validate_quasipoly_recurrence_tree_v3`;
- consistent with the producer's real scan convention: `|G|` checks for exact empty and `2|G|` checks for a nonempty result with second-pass coset audit.

Any disagreement is `rejected_producer_proof` rather than an exact result.

## Independent replay

rev252 independently enumerates the represented group again from its Schreier chain. It does not reuse the producer's enumerated element list. For a nonempty producer result it first verifies that the representative and the complete claimed right coset lie inside the represented group.

It then builds a rev251 immutable replay certificate from:

- the frozen source/target strings;
- the independently enumerated candidate group;
- the producer-derived claimed match set.

The rev251 verifier independently proves group closure, replays every candidate action, reconstructs the target-stabilizer right coset, and compares the complete match set. `admitted_exact` is returned only when that replay is `verified_exact`; for nonempty results the replayed target-stabilizer order must also equal the producer coset subgroup order.

## Fail-closed regression coverage

The dedicated rev252 tests cover:

1. a nonidentity C7 transporter admitted only after independent replay;
2. exact-empty C5 admission;
3. repeated-color C5 with nontrivial target stabilizer;
4. group-order rejection before producer execution;
5. quadratic replay-budget rejection before producer execution;
6. tampered certified group order;
7. a deliberately wrong producer right coset rejected by complete replay;
8. tampered recurrence-accounting evidence;
9. opaque color rejection before producer execution.

The dedicated workflow also reruns the inherited rev170 small-order terminal tests and the rev251 exact-result replay tests.

## Parallel safety

The implementation is confined to the rev252 claim's reserved files:

- `proof_carrying_small_order_production_admission_v1.py`;
- `test_proof_carrying_small_order_production_admission_rev252.py`;
- this audit note;
- the rev252 smoke workflow.

The already-main-visible `j-rev252-session-hourly-refire.yml` remains unchanged. `MAIN.md`, shared solver modules, shared workflows, sibling claims, and concurrent rev253+ branches are not modified.

## Strict boundary

This is an acceptance/replay integration for one finite small-order exact terminal. It does not prove that structural recursion above the small-order gate is complete, does not close the other CRX3 algorithmic consumers, corrected Split-or-Johnson, global String-Isomorphism/GI, practical AGI delivery, or the AGI root. The repository state remains `NOT_AGI`.
