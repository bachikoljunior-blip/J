# AGI-GI rev228 — single-test execution-linked resource envelope

## Resolved leaf

CRX2 child 2.2.2.3 required one finite budget for the complete execution of a
single local-certificate test set `T`.  rev224--rev227 exposed complete phase
bounds, but four independent caps did not prove that their sequential
composition fit one budget.

## Implementation

- `SingleTestResourceEnvelope` records every admitted/executed phase in order,
  charges its conservative bound exactly once, and verifies the remaining
  budget after each phase.
- The A(T) preimage, every before/after giant-action audit, affected-segment
  quotient/kernel recursion, and parent-coset reassembly now draw from the same
  remaining budget.
- Quotient and reassembly preflight sequentially.  Reassembly receives only the
  budget left after the quotient bound and both reject before quotient
  preparation if their sum cannot fit.
- A rejected phase remains in the evidence with `executed=False` and contributes
  no charge.  An executed phase cannot appear twice without two explicit phase
  records.
- The strict theorem relation uses one `4_000_000_000` default single-T budget;
  legacy per-phase caps remain available only when the single cap is disabled.

## Evidence and limits

- The new regressions exercise all five phases on an exact non-full S5 case,
  exact budget exhaustion between preimage and the first giant audit, combined
  quotient/reassembly rejection before execution, and rejection of ambiguous
  mixed cap modes.
- Existing rev224--rev227 phase tests remain unchanged and pass.
- This resolves the complete single-T resource sum only.  Complete all-T
  scheduling, test-set multiplicity, source/target comparison, original-root
  quasipolynomial charging, generality, autonomy, and practical delivery remain
  unresolved.

AGI status remains `NOT_AGI`.
