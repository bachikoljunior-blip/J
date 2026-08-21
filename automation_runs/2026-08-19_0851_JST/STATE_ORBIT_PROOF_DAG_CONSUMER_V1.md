# State-orbit exact terminal proof-DAG consumer v1

## Scope

This change closes one concrete CRX3 algorithmic-consumer gap without changing
Johnson, Design, relation-image, S1, or main-revision ownership paths.
`proof_carrying_state_orbit_candidate_v1.py` already supplied an exact candidate
string-isomorphism terminal with a finite pre-execution resource envelope and a
`RecurrenceAccountingNode`.  Its exact `ProofCarryingCoset`, however, carried no
`proof_identity`, so `proof_dag_accounting_v1.validate_execution_proof_dag`
rejected it as `missing_root_proof_identity`.

## Resolution

The terminal now freezes a dedicated immutable identity containing:

- the complete deterministic Schreier-chain snapshot and candidate representative;
- oriented source and target string snapshots;
- original root and current domain;
- a versioned solver/transporter identity; and
- the finite `max_work` gate plus every derived state-orbit envelope value.

Only admitted exact executions receive the identity.  A work-cap rejection stays
nonexact and unshareable.  Hashable but opaque colors may still be solved exactly,
but their identity is marked non-replay-stable so common proof-DAG storage fails
closed instead of treating a process-local representation as mathematics.

`validate_state_orbit_candidate_proof_identity` separately checks identity type,
full equality, replay stability, exact-terminal flags, and exposed recurrence
measure.  The common proof-DAG verifier remains the authority for recurrence and
original-root cost certification.

## Regression gates

`test_state_orbit_proof_dag_consumer_v1.py` checks:

1. a nonidentity candidate exact result is accepted as a one-node execution proof DAG;
2. changing only `max_work` changes the execution identity even when both answers are exact;
3. an opaque color executes but cannot be reused as a stable DAG identity;
4. work-cap rejection remains identity-free and measure tampering is rejected; and
5. a tampered derived envelope is rejected before any proof identity is issued.

The smoke workflow also reruns the original rev239 state-orbit terminal tests and
rev220 proof-DAG accounting tests.

## Parallel-safety boundary

Reserved implementation paths are limited to the state-orbit terminal, its new
regression/report, and two uniquely named workflows.  This work does not modify
`MAIN.md`, current revision ledgers, active Johnson/Design/relation-image/S1 files,
or any concurrently reserved workflow.
