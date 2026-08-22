# AGI-GI rev292 — Johnson reduction / recursive-handoff composition

## Status

- Revision: `292`
- AGI state: `NOT_AGI`
- Scope: `w1r-h6/corrected-split-or-johnson/larger-ground-johnson-relational-reduction-handoff-composition`
- Branch: `agi-gi-rev292-soj-johnson-reduction-handoff-composition-session-20260822-1239-b743c9e1`
- Active claim: `agi/run-history/active/chatgpt-session-j-rev292-soj-johnson-reduction-handoff-composition-20260822T123900JST-b743c9e1.json`

## Problem isolated by this revision

The larger-ground primitive Johnson path had two intentionally separate sibling contracts:

1. rev287 constructs exact `J(v,k) -> v` relational-reduction evidence from a complete Johnson embedding and ambient generators.
2. rev291 accepts caller-supplied relational-reduction evidence and binds it to a strictly smaller recursive accounting child.

That separation avoids branch coupling, but it leaves a boundary obligation: a consumer must prove that the reduction snapshot embedded in the rev291 handoff is exactly the construction certified by rev287, rather than a look-alike object with changed parameters, transport flags, cost bound, digest, or recurrence child.

rev292 supplies only that missing cross-certificate boundary. It imports neither branch-only sibling module and writes no sibling path.

## Certificate implemented

`corrected_soj_johnson_reduction_handoff_composition_v1.py` exports:

- `JohnsonReductionConstructionSnapshot`
- `JohnsonRecursiveHandoffSnapshot`
- `JohnsonReductionHandoffCompositionCertificate`
- `certify_johnson_reduction_handoff_composition(...)`
- `replay_johnson_reduction_handoff_composition(...)`

The certifier is structural and fail-closed. It consumes the public fields of construction evidence and a recursive-handoff result without relying on their concrete Python classes.

### Construction-side replay

Before accepting the rev287-shaped object, rev292 independently checks:

- strict schema, status, and boolean fields;
- `v >= 4`, `2 <= k <= v-2`, and `source_action_degree = C(v,k)`;
- strict progress from `C(v,k)` to ground degree `v`;
- exact/canonical/progress certification;
- exact solution transport, ambient-membership transport, and explicit complement handling;
- finite multiplicative cost within its certified upper bound;
- canonical lowercase SHA-256 reduction identity;
- a complete, duplicate-free copy of all `k`-subsets;
- exact equality between the supplied incidence stars and the stars reconstructed from those subsets;
- every induced ground generator is a permutation of degree `v`;
- exact replay of the rev287 construction-work formula.

It then digests the vertex subsets, incidence stars, induced ground generators, and normalized construction envelope.

### Handoff-side replay

Before composing the rev291-shaped object, rev292 independently checks:

- exact certified larger-ground handoff status and schema;
- unresolved canonical primitive-Johnson ground-cap semantics without manufactured terminal exactness or cost certification;
- exact equality of every shared reduction field with the normalized construction snapshot;
- `charged_log2_reduction_cost = log2(max_multiplicative_cost)`;
- an acyclic, finite recurrence-accounting tree;
- strict node types, canonicality, local-cost certification, valid measures, terminal discipline, positive multiplicities, and permitted progress operations;
- auxiliary-shrink and small-aux-reset inequalities throughout the full tree;
- independent log-sum-exp work composition and quasipolynomial-envelope replay;
- equality of validation status, work bound, allowed bound, node count, and maximum depth;
- one multiplicity-one root edge from the represented Johnson action degree to the constructed ground degree;
- exact replay of the rev291 handoff SHA-256 payload.

Only after all checks pass does rev292 emit one deterministic composition digest binding:

- the normalized construction digest;
- the rev287 reduction identity;
- the rev291 handoff digest;
- the full recurrence-accounting tree digest;
- root, represented-action, and child-ground measures;
- the configured shrink fraction.

## Fail-closed regressions

The dedicated test file exercises 18 cases, including:

- successful certification and replay;
- uncertified or non-strict construction fields;
- incomplete Johnson embeddings;
- incidence-star mismatch;
- malformed ground permutations;
- incorrect construction-work accounting;
- mismatch of every shared reduction boundary field;
- uncertified handoffs;
- forged handoff digests;
- wrong represented-action and child-ground measures;
- insufficient shrink;
- validation work/count disagreement;
- accounting cycles;
- non-finite cost values;
- replay after evidence mutation.

Local validation before publication:

```text
18 tests passed
python -m py_compile: success
```

Exact-head GitHub Actions results are recorded separately by the dedicated rev292 smoke workflow and the repository parallel-admission workflow.

## Non-interference

This revision is additive and restricted to the paths reserved by the rev292 schema-v2 active claim. In particular it does not:

- modify or import rev287 or rev291 branch-only implementation files;
- modify any sibling claim, branch, PR, workflow, or reserved path;
- cancel or rerun another workflow;
- modify `MAIN.md` or shared coordination implementation;
- merge, rebase, force-push, or close sibling work.

The hourly re-fire workflow is separately installed on `main`; it only emits a deduplicated continuation request after 55 minutes without rev292 claim, branch, or PR activity, and uses non-cancelling concurrency.

## Non-claims and remaining work

rev292 does not execute the recursive String Isomorphism child. It does not prove the complete corrected Split-or-Johnson theorem, quasipolynomial GI, or AGI. Its result is a narrower machine-checkable statement: when the two sibling certificates are supplied, the construction consumed by the handoff is exactly the certified Johnson-ground construction, and the complete recurrence-accounting envelope replays consistently.
