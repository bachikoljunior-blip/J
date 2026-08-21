# rev266 — implicit relation parent exact-outcome contract

## Scope

This revision is the collision-free continuation owned by
`chatgpt-session-j-rev266-parent-outcome-contract-20260822T0751JST-9e47c886`.
It adds an evidence-only boundary after the two independently verified parent
outcome routes:

- rev261 nonempty parent promotion: `exact_implicit_relation_parent_coset`;
- rev263 exact-empty parent promotion: the three mechanically certified
  `exact_empty_parent_*` statuses.

The contract does **not** rerun either semantic verifier. It does not construct
an implicit value-preserving image coset, a paired original-domain preimage, a
resource envelope, or a production caller. Those remain separate claims.

## Problem

The two exact parent outcomes currently have different runtime result types and
live on independently developed branches. A later caller must not infer a
single parent conclusion merely from a truthy `exact` field, nor silently pick
one result if both nonempty and empty evidence are presented.

rev266 therefore introduces a replay-stable transcript and a fail-closed
normalizer. The transcript binds:

- the source verifier revision and exact status;
- the typed outcome kind (`nonempty` or `exact_empty`);
- exact/complete flags;
- original and auxiliary degrees;
- caller-supplied SHA-256 identities for the source relation, target relation,
  and already-verified upstream artifact; and
- a canonical SHA-256 digest over all transcript fields.

The normalizer additionally receives the exact source/target relation digests
and parent domain degree expected by the caller. It accepts exactly one valid
transcript and rejects every ambiguous or mismatched case.

## Exact admissions

### Nonempty

Only an already-verified rev261 object with all of the following is admitted:

- status `exact_implicit_relation_parent_coset`;
- `exact is True`;
- `complete is True`;
- a non-`None` right coset;
- positive auxiliary degree at normalization time.

The normalized status is `exact_parent_outcome_nonempty`.

### Exact empty

Only an already-verified rev263 object with `exact is True`, `complete is True`,
and one of these statuses is admitted:

- `exact_empty_parent_domain_size_mismatch`;
- `exact_empty_parent_relation_signature_mismatch`;
- `exact_empty_parent_feature_inventory_mismatch`.

The feature-inventory route must identify a positive auxiliary degree. The
normalized status is `exact_parent_outcome_empty`.

## Fail-closed cases

The normalizer withholds an exact parent outcome when any of the following is
observed:

- no exact transcript;
- more than one transcript, including a nonempty/empty contradiction;
- wrong runtime transcript type or schema version;
- malformed digest/degree fields;
- canonical transcript-digest corruption;
- source relation, target relation, or domain-degree mismatch against caller
  context;
- a transcript that is not exact and complete;
- a source revision/status inconsistent with its typed outcome; or
- an unknown outcome kind.

No branch priority or best-effort reconciliation is performed.

## Parallel boundary

rev266 changes only the paths reserved in its durable claim. In particular it
does not modify rev261, rev262, rev263, rev264, rev265, the CRX3 proof-DAG work,
`MAIN.md`, shared coordination tooling, or sibling workflows/branches/PRs.

## Strict result boundary

This is a replayable **evidence contract**, not a production parent solver. It
proves that one already independently verified exact parent outcome can be
represented and rebound to an exact caller context without ambiguity or silent
corruption. It does not establish the upstream semantic evidence itself and
does not close CRX1, Graph Isomorphism, or AGI. State remains `NOT_AGI`.
