# AGI-GI rev1200 — recursive production lineage closure

## Scope

This leaf owns only `w1r-h6/corrected-split-or-johnson/larger-ground-recursive-production-lineage-closure` under claim `chatgpt-session-j-rev1200-soj-recursive-production-lineage-closure-20260822T155100JST-fc1ee447`.

It is deliberately file-disjoint from the active rev1100 main post-replay seal, rev1000 post-replay coherence envelope, rev900 provenance/total-cost binding, rev950 proof-DAG/main-sync work, and every earlier producer/accounting leaf. It does not modify or import sibling branch-only implementations.

## Gap closed

rev1100 intentionally emits a compact main-anchored seal. rev900 retains additional explicit recursive lineage fields (`recursive_provenance_identity`, `result_lift_digest`, `accounting_binding_digest`, `child_result_identity`, `coherence_identity`, and `total_cost_binding_identity`) that are cryptographically upstream of the compact rev1100 seal but are not re-exposed by it.

rev1200 supplies a fail-closed downstream audit/consumer boundary that:

1. independently recomputes rev900's deterministic `total_cost_binding_identity` from the public rev900 output tuple;
2. independently recomputes rev1100's deterministic `seal_identity` from the public rev1100 output tuple;
3. requires both certificates to name the same main commit, main-provenance identity, caller binding/replay envelope, reduction, production provenance, parent/child measure, construction-cost binding, power-of-two bound, and exact logarithmic charge;
4. preserves `exact_empty` versus nonempty semantics without coercion;
5. retains the rev900 accounting/result/coherence lineage alongside rev1100's post-replay/main-seal identities in one deterministic closure identity.

The adapter rechecks strict positive shrink and the exactly-once construction charge (`charged_log2_reduction_cost == log2(construction_multiplicative_cost_bound)`) on both public certificates.

## Strict boundary

This certificate does **not** execute recursive String Isomorphism, reconstruct the Johnson reduction, replay noncompact upstream mathematical proofs, authenticate Git reachability/blob provenance, infer whether sibling PRs are merged, or establish corrected Split-or-Johnson/GI/AGI. Deterministic identity replay proves only self-consistency of the public certificate formulas plus the explicit cross-certificate equalities checked here.

rev900 and rev1100 remain independently owned upstream leaves. rev1200 is therefore draft-only until their contracts stabilize and exact-head CI/admission is green. `agi_state` remains `NOT_AGI`.

## Focused regressions

The standard-library suite covers successful nonempty and exact-empty closure, both upstream identity replays, main/caller/provenance/reduction/cost drift, outcome mismatch, strict-shrink failure, power-of-two and exact-log2 failure, strict booleans, digest format rejection, and closure replay tampering.
