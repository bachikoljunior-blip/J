# AGI-GI rev1300 — recursive production lineage closure

## Scope

This leaf owns only `w1r-h6/corrected-split-or-johnson/larger-ground-recursive-production-lineage-closure` under claim `chatgpt-session-j-rev1300-soj-recursive-production-lineage-closure-20260822T155500JST-4b4cf2ab`.

It is the collision-retreated continuation of this session's superseded rev1200 SOJ lineage branch. A different session had already claimed target revision 1200 for homogeneous-block quotient String-Isomorphism, so rev1200 PR #258 was closed unmerged and this work moved to rev1300 with new paths. The earlier rev1200 claim/branch/PR/workflows are not modified by rev1300.

rev1300 is deliberately file-disjoint from rev1100 main post-replay seal, rev1000 post-replay coherence envelope, rev900 provenance/total-cost binding, the independently owned canonical-main-source coordination hardening, homogeneous-block quotient work, CRX scopes, `MAIN.md`, and shared recurrence/proof-DAG/coordination implementation. It does not import sibling branch-only implementations.

## Gap closed

rev1100 intentionally emits a compact main-anchored seal. rev900 retains additional explicit recursive lineage fields (`recursive_provenance_identity`, `result_lift_digest`, `accounting_binding_digest`, `child_result_identity`, `coherence_identity`, and `total_cost_binding_identity`) that are cryptographically upstream of that compact seal but not re-exposed by it.

rev1300 adds a fail-closed downstream audit/consumer boundary that:

1. independently recomputes rev900's deterministic `total_cost_binding_identity` from the public rev900 output tuple;
2. independently recomputes rev1100's deterministic `seal_identity` from the public rev1100 output tuple;
3. requires both certificates to name the same main commit, main-provenance identity, caller binding/replay envelope, reduction, production provenance, parent/child measure, construction-cost binding, power-of-two bound, and exact logarithmic charge;
4. preserves `exact_empty` versus nonempty semantics without coercion;
5. retains the rev900 accounting/result/coherence lineage alongside rev1100's post-replay/main-seal identities in one deterministic closure identity.

The adapter rechecks strict positive shrink and the exactly-once construction charge (`charged_log2_reduction_cost == log2(construction_multiplicative_cost_bound)`) on both public certificates.

## Coordination boundary

A separately owned active coordination hardening changes phase-admission generation so `registry_source_sha` is bound to canonical main ancestry rather than an arbitrary synthetic/branch head. This session already observed and removed one unsafe rev1200 evidence snapshot created under the older behavior.

Therefore rev1300 reserves, but deliberately does not materialize, its `attempt_solution` or `publish` evidence while that hardening remains independently active. The dedicated workflow asserts those evidence files are absent. Repository-wide phase admission is expected to remain fail-closed for rev1300 until the canonical-main-source contract stabilizes; rev1300 does not modify or rerun that coordination work.

## Strict boundary

This certificate does **not** execute recursive String Isomorphism, reconstruct the Johnson reduction, replay noncompact upstream mathematical proofs, authenticate Git reachability/blob provenance, infer whether sibling PRs are merged, close corrected Split-or-Johnson/GI, or establish AGI. Deterministic identity replay proves only self-consistency of the public certificate formulas plus the explicit cross-certificate equalities checked here.

rev900 and rev1100 remain independently owned upstream leaves. rev1300 is draft-only while their contracts and coordination infrastructure stabilize. `agi_state` remains `NOT_AGI`.

## Focused regressions

The standard-library suite covers successful nonempty and exact-empty closure, both upstream identity replays, main/caller/provenance/reduction/cost drift, outcome mismatch, strict-shrink failure, power-of-two and exact-log2 failure, strict booleans, digest format rejection, and closure replay tampering.
