# AGI-GI rev295 — signed Johnson ground exact terminal proof-DAG consumer

## Selected unresolved leaf

This revision claims only `crx3/algorithmic-consumers/signed-johnson-ground-exact-terminal-proof-dag`.

The repository already contains two independent main-integrated substrates:

1. rev176's exact small-order signed Johnson ground relational String-Isomorphism terminal, which enumerates only the represented signed ground group after a faithful Johnson lift and returns a proof-carrying exact right coset or exact empty result; and
2. rev220's conservative execution proof-DAG, hardened by rev289, which deduplicates proof storage by replay-stable identity while still charging every execution occurrence and enforcing the original-root quasipolynomial envelope.

rev295 connects only those two substrates. It does not change either implementation.

## Replay identity

The consumer freezes the complete deterministic Schreier-chain group representation, oriented source and target strings, root and point-domain measures, solver version, group-order and recognition resource gates, certified Johnson ground/subset parameters, signed-group order, exact execution count, recognition count, terminal status, and local cost charge.

The exact terminal payload is independently rechecked before the shared DAG is invoked:

- only `exact_signed_johnson_ground_relation_coset` and `exact_empty_signed_johnson_ground_relation` are admissible;
- canonical, exact, local-cost-certified, terminal-certified leaf structure is mandatory;
- the nonempty case must carry an original-domain right coset and exactly two represented-group scans; the empty case must carry no coset and exactly one represented-group scan;
- the signed-group order must still fit the frozen polynomial/hard gate;
- the rev176 local cost formula is recomputed mechanically from group order, Johnson point degree, subset size, and ground size;
- the recurrence leaf must agree exactly with the frozen root, ground measure, operation kind, local cost, and terminal flags;
- opaque value snapshots or non-finite charges are never marked replay-stable.

If any condition fails, no reusable proof identity is exposed.

## Proof-DAG admission

A valid exact proof is attached to the immutable rev295 identity and then passed unchanged to `validate_execution_proof_dag`. The shared validator remains responsible for recurrence replay, identity collision/cycle checks, conservative occurrence charging, non-finite envelope rejection, and the original-root quasipolynomial bound.

No branch-only sibling implementation is imported. Shared `proof_dag_accounting_v1.py`, rev176, `MAIN.md`, coordination implementation, and sibling claims/workflows are read-only dependencies.

## Regression boundary

Focused tests cover:

- exact nonempty PGL(2,8) on J(9,2) admission;
- exact-empty admission;
- preserved fail-closed group-order cap behavior;
- opaque values that execute exactly but cannot be shared by proof identity;
- proof-identity tampering;
- terminal accounting drift;
- non-finite quasipolynomial envelope rejection; and
- strict root-parameter validation.

Inherited rev176 and rev289/rev220 regression files run in the dedicated smoke workflow.

## Non-claims

This does not alter Johnson recognition, close larger signed-ground recursion, wire corrected Split-or-Johnson production, solve GI, establish practical AGI delivery, or establish AGI. Repository state remains `NOT_AGI`.
