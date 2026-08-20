# AGI-GI rev229 — complete all-test multiplicity preflight

## Direct attempt and decomposition

The remaining CRX2 all-test leaf contains three distinct obligations:

1. reserve and execute every canonical `T` on one side with exact multiplicity;
2. compare source and target certificate evidence canonically;
3. charge comparison, aggregation, t-WL, and Design consumers back to the
   original root degree.

rev229 resolves the first obligation.  The other two remain explicit leaves.

## Implementation

- `AllTestResourceEnvelope` computes `C(m,t) * per_test_work_cap` with exact
  arbitrary-precision integers before the first certificate runs.
- A finite all-test cap must admit the complete canonical schedule.  The
  engineering `max_test_sets` counter is not treated as a complexity proof.
- Execution evidence records the number of completed tests, accumulated rev228
  charges, and the exact unexecuted suffix after an early unknown.
- A complete record is rejected unless every reserved test set executed.
- Strict theorem aggregation receives a finite default all-test budget; bounded
  non-theorem regressions remain explicitly separate.

## Existing-world inclusion audit

This applies admission control/WCET reservation and batch-scheduler cardinality
accounting to Babai's canonical all-`T` local-certificate family.  Reservation
is not promoted to empirical performance, and a combination cap is not promoted
to a quasipolynomial proof without the remaining original-root lift.

AGI status remains `NOT_AGI`.
