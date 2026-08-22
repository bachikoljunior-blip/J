# AGI-GI rev270 — implicit relation-image resource execution ledger

## Scope

Rev270 advances only `crx1/bounded-arity-relation-image/implicit-generator-group/original-root-resource-execution-ledger`.  It does not change the semantic String-Isomorphism solver, the active rev269 exact-empty parent bridge, rev268 production orchestration, rev267 paired preimage, rev265 resource envelope, rev262 value-coset implementation, any CRX3 proof-DAG branch, or `MAIN.md`.

The root state remains **NOT_AGI**.  This revision is resource-accounting infrastructure for one unresolved String-Isomorphism path and is not evidence for generality, performance, autonomy, independent reproduction, or practical AGI delivery.

## Collision-safe rescope

At the start of this continuation, the next visible semantic gap was the exact-empty auxiliary-image to exact-empty parent implication.  Before writing that implementation, the active registry was re-read and a fresh rev269 claim was found for exactly that scope.  Rev270 therefore moved to a disjoint resource-accounting sibling and reserves four new problem-state files plus one replayable phase-admission evidence record.

## Existing machinery reused

Rev250 already provides the repository's thread-safe phase-start capability ledger.  It enforces canonical phase order, one active capability at a time, cross-instance separation, single consumption, bounded charges, replay rejection, abort generation changes, and preservation of the complete unexecuted suffix.  Duplicating those mechanics for the implicit relation-image pipeline would create a second accounting protocol, so rev270 adapts the six-phase resource contract to rev250 instead.

The still-active rev265 branch defines the intended pre-execution resource shape.  Rev270 deliberately does **not** import that branch-only module or edit any of its files.  Instead, `implicit_relation_resource_execution_ledger_v1.py` structurally validates the published rev265-style contract: certified status and flags, original-root degree lift, compatible domain/image order bounds, exact canonical six-phase names, the sum of all phase reservations, and the caller-derived finite `max_work` cap.

## Canonical execution boundary

The six phases are fixed as:

1. `induced_action`
2. `domain_schreier`
3. `image_schreier`
4. `value_coset_intersection`
5. `paired_preimage`
6. `verification`

Before any phase begins, the wrapper asks rev250 for the single-use start ticket for exactly the next phase.  That ticket snapshots the whole remaining suffix and its work reservation.  A phase may be committed only with a nonnegative charge no larger than its own bound and without consuming the reserved suffix for later phases.  Replay, cross-instance use, out-of-order issue, overcharge, or context/reservation drift fails closed.

The wrapper hashes the complete admitted resource context and checks that digest before every ticket operation.  Once all six phases have committed, finalization produces a replay-stable resource execution digest over the original envelope digest, all reservations, and all actual phase charges.

## Exactness boundary

The final certificate proves **resource-accounting completeness only**.  It intentionally has no String-Isomorphism exactness field and cannot promote an unresolved, empty, or nonempty semantic solver result.  Semantic exactness remains the responsibility of rev262/rev267/rev268/rev269 and their independently validated parent contracts.  This separation prevents a finite-budget proof from being mistaken for a mathematical SI proof.

## Regression boundary

The dedicated regression suite checks an admitted six-phase plan, whole-suffix reservation before the first phase, exactly-once phase advancement, complete finalization, out-of-order rejection, consumed-ticket replay rejection, cross-instance rejection, phase overcharge rejection, abort/reissue generation separation, rejected/wrong-status envelope rejection, phase-order drift rejection, aggregate/order-gate drift rejection, post-admission context drift rejection, and incomplete-finalization rejection.  The workflow also reruns the inherited rev250 ticket-ledger regression suite.

No AGI achievement is claimed.
