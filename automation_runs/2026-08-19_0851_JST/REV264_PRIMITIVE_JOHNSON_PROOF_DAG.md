# REV264 — primitive Johnson exact terminal → shared proof-DAG consumer

## Boundary

This revision closes one narrow CRX3 algorithmic-consumer boundary: the already exact,
bounded `primitive_johnson_ground_terminal_v1` execution can now be wrapped in a complete,
replay-stable mathematical/resource identity and admitted to the existing rev220
conservative execution proof-DAG verifier without modifying either shared implementation.

It does **not** change Johnson recognition, the terminal's search, S1 dispatch, candidate
coset logic, recurrence rules, or the common proof-DAG implementation. It is a sibling of
the active state-orbit proof-DAG consumer and the rev252 small-order production admission.

## Construction

`primitive_johnson_proof_dag_consumer_v1.py` freezes:

- the complete deterministic Schreier-chain representation of the supplied group;
- the oriented source and target strings;
- the original root/domain measure;
- the exact terminal resource gates (`polylog_power`, `max_ground_degree`,
  `max_recognition_nodes`); and
- a versioned primitive-terminal/common-DAG solver identity.

Only an exact, canonical, locally cost-certified and terminal-certified execution can carry
the identity. Opaque values are allowed to be evaluated by the mathematical terminal but
are rejected for shared replay, and the returned proof has no reusable identity in that
case. Nonexact/fail-closed terminal results also receive no identity.

The attached identity is independently checked before calling
`validate_execution_proof_dag`; rev220 then independently validates the recurrence tree,
identity-DAG structure, occurrence charge, and original-root quasipolynomial envelope.

## Focused regressions

The rev264 suite checks:

1. an exact `J(5,2)` coset execution reaches the shared DAG and preserves a known witness;
2. exact emptiness is equally admissible and conservatively charged;
3. a non-Johnson unresolved terminal remains identity-free;
4. opaque colors fail shared replay closed while preserving the exact mathematical result;
5. a tampered root/resource identity is rejected before DAG reuse.

The dedicated workflow also reruns the inherited rev173 primitive-Johnson terminal tests and
rev220 proof-DAG accounting tests.

## Parallel safety and status

The revision adds only five claim-reserved paths. It does not touch `MAIN.md`,
`proof_dag_accounting_v1.py`, `s1_string_isomorphism_v4.py`,
`primitive_johnson_ground_terminal_v1.py`, any active CRX1 rev258–rev263 implementation,
rev252, or the state-orbit proof-DAG PR.

This is one bounded CRX3 consumer advance. Corrected Split-or-Johnson, complete global
String Isomorphism/GI, practical AGI delivery, and AGI remain unresolved. State:
`NOT_AGI`.
