# Rev250: original-root phase-start ticket ledger

## Scope

This revision adds a collision-free CRX3 boundary without modifying the shared
Design, S1, primitive-Johnson, relation-image, or proof-DAG files reserved by
rev245 through rev249.  It turns a pre-admitted phase budget into explicit,
single-use phase-start capabilities.

The implementation is deliberately structural: it can read the existing
`DesignOriginalRootPipelineResourceEnvelope` fields without importing or
rewriting that module.  The existing immutable phase recorder remains the
source of the actual charge; this ledger verifies the recorded successor before
consuming the matching ticket.

## Contract

For phase bounds `b_0, ..., b_(m-1)`, completed actual charges
`q_0, ..., q_(i-1)`, and aggregate reservation `W`, a ticket for phase `i` is
issued only when

```
sum(q_j for j < i) + sum(b_j for j >= i) <= W <= max_work.
```

The ticket snapshots the canonical phase index, charged prefix, complete
unexecuted suffix, and both suffix bounds.  A commit accepts only
`0 <= q_i <= b_i`.  Therefore

```
sum(q_j for j <= i) + sum(b_j for j > i)
    <= sum(q_j for j < i) + sum(b_j for j >= i)
    <= W,
```

so beginning and completing one phase cannot silently spend the reservation of
any later phase.

## Fail-closed properties

- Only the next canonical phase can receive a ticket.
- At most one ticket is active per ledger instance.
- Commit and abort retire the capability and advance a monotone generation.
- A replay, stale ticket, foreign ledger instance, changed bound, rewritten
  prior charge, malformed envelope successor, or overcharge is rejected.
- Ticket consumption is guarded by an `RLock`; two concurrent commits against
  one ledger yield exactly one winner.
- Failed validation occurs before mutation, so the active ticket remains usable
  after a bad charge or malformed envelope result is rejected.
- Python arbitrary-precision integers are retained throughout; no fixed-width
  overflow can weaken the reservation inequality.

## Validation

`test_phase_start_ticket_ledger_rev250.py` covers suffix reservation at issue,
canonical ordering, overcharge rollback, replay and cross-instance rejection,
abort/reissue, envelope reconstruction and successor validation, concurrent
double commit, arbitrary-precision bounds, and completion.

This is a resource-accounting boundary only.  It does not discharge the open
CRX1/CRX2/CRX3 mathematical obligations and does not change the repository's
`NOT_AGI` state.
