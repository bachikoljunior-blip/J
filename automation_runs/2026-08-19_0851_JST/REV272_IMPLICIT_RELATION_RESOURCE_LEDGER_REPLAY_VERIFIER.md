# AGI-GI rev272 — implicit relation resource-ledger replay verifier

## Boundary

rev272 adds an **independent structural replay verifier** for the six-phase implicit relation-image resource ledger. It does not import the concurrently owned rev265 resource-envelope module or rev270 execution-ledger module and does not modify their branches or PRs.

The canonical phases are `induced_action`, `domain_schreier`, `image_schreier`, `value_coset_intersection`, `paired_preimage`, and `verification`.

## What is verified

Given a serialized admitted resource context and a serialized rev250-style ledger snapshot, the verifier reconstructs the rev270 public envelope digest and the rev250 public plan digest, then checks:

- exact canonical six-phase order and six admitted phase bounds;
- original-root degree lift and image-order gates;
- aggregate reservation equality and `max_work` containment;
- completed phases are an exact prefix and charges are nonnegative integers within each phase bound;
- `charged_work` equals the phase-charge sum;
- `unexecuted_suffix` is exactly the canonical tail and retains its complete reservation;
- aggregate/max-work remaining fields replay exactly;
- no active ticket survives into replay evidence;
- consumed/aborted ticket histories are duplicate-free, disjoint, and generation-consistent;
- completion is accepted only when all six phases are charged.

A valid incomplete prefix is certified only as resource-accounting replay evidence. A valid complete ledger is certified only as **resource complete**. The result deliberately fixes `semantic_exactness_certified=False`; it cannot turn a resource certificate into a String-Isomorphism result.

## Parallel-safety boundary

This revision is additive. It writes only the rev272 claim-reserved workflow, verifier, focused tests, and this memo. It does not modify `MAIN.md`, rev269/rev270/rev271 paths, rev268 orchestration, rev267 preimage, rev265 envelope, CRX3 proof-DAG consumers, rev252, sibling claims, or sibling workflows.

## Regression surface

Focused tests cover complete and incomplete valid ledgers, abort generation, envelope/plan digest tampering, out-of-order and duplicate prefixes, phase overcharge, charged-work mismatch, suffix tampering, remaining-work tampering, active-ticket rejection, ticket token replay/overlap, generation mismatch, bool-as-integer rejection, false completion, and aggregate mismatch.

AGI state remains `NOT_AGI`.
