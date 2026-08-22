# AGI-GI rev289 — shared proof-DAG envelope input hardening

## Scope

This revision closes one shared fail-open validation gap at the execution proof-DAG accounting boundary. It modifies only the main-integrated `proof_dag_accounting_v1.py` validator plus a dedicated regression and smoke workflow.

The trigger was an independently observed consumer-side hazard: `external_log2_cost_bound=float("nan")` passed the old `external_log2_cost_bound < 0` check, propagated `NaN` into `total`, and then also passed `total > allowed` because comparisons with `NaN` are false. A malformed envelope argument could therefore reach the final certified return.

## Contract

`validate_execution_proof_dag` now fails closed before recurrence replay or floating-point comparison unless:

- `original_root_n` is a positive strict integral value and not a boolean/coercible float/string;
- `quasipoly_power` is a nonnegative strict integral value;
- an explicit `polynomial_lift_degree`, when supplied, is a positive strict integral value;
- `external_log2_cost_bound` and `quasipoly_constant` are finite nonnegative real values and not booleans/strings;
- the computed quasipolynomial envelope remains finite;
- the independently returned recurrence work bound remains finite;
- proof-DAG occurrence charging and the final external-plus-DAG charge remain finite.

All existing mathematical checks remain unchanged: recurrence certification, polynomial `n+n^2` lift restriction, proof identity stability/collision/cycle checks, occurrence charging, tree/DAG charge agreement, and the original-root envelope comparison.

## Parallel boundary

This scope is independent of active rev275-rev288 implementation paths. In particular it does not import or modify branch-only rev279/rev280 proof-DAG consumers, corrected Split-or-Johnson branches, block-action kernel work, state-orbit work, CRX1/CRX2 production paths, `MAIN.md`, or coordination registry implementation.

The shared proof-DAG validator was explicitly left outside rev279's consumer claim; rev289 claims only this shared hardening boundary and its dedicated test/doc/workflow paths.

## Validation

The dedicated smoke compiles the shared validator and focused regression, reruns inherited rev220 proof-DAG accounting tests, runs rev289 malformed-input regressions, and rejects branch-only sibling dependencies.

Root state remains `NOT_AGI`; this is a correctness hardening change, not a closure claim for CRX3, GI, or AGI.
