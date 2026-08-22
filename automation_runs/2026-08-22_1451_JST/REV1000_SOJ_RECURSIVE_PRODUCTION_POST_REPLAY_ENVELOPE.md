# AGI-GI rev1000 — recursive production post-replay coherence envelope

## Scope

This leaf owns only `w1r-h6/corrected-split-or-johnson/larger-ground-recursive-production-post-replay-coherence-envelope` under claim `chatgpt-session-j-rev1000-soj-recursive-production-post-replay-envelope-20260822T1451JST-0b1c7a15`.

It is downstream of, and file-disjoint from, the active rev720 construction-cost-provenance leaf and the active rev900 provenance/total-cost leaf. It also does not modify or import rev340/rev360/rev400/rev500/rev600/rev650/rev700/rev800 branch-only implementations, `MAIN.md`, CRX scopes, shared recurrence code, shared proof-DAG code, or shared coordination implementation.

## Contract

rev1000 deliberately uses a post-replay boundary instead of guessing branch-only upstream class layouts. Each upstream owner must first replay its own deterministic certificate and expose a strict normalized compatibility view. A view is admitted only when:

- the replay gate is literal `True`, and `exact` / `complete` are literal `True`;
- the result preserves `exact_empty` versus `nonempty`;
- parent and child measures are strict positive integers with `child < parent`;
- reduction, production-provenance, construction-cost, and upstream identities are canonical `sha256:<64-hex>` values;
- the conservative construction multiplicative bound is a finite integral power of two; and
- the charged reduction cost is exactly `log2` of that bound.

The final envelope accepts exactly one `production_cost_provenance` view and one `provenance_total_cost` view. It requires field-for-field equality of outcome, parent/child measures, reduction identity, production-provenance identity, construction-cost-binding identity, conservative construction bound, and exact log2 charge. The two upstream output identities themselves are expected to be different and are both retained. A deterministic envelope identity seals both replay-view identities and the shared compatibility tuple.

## Fail-closed boundary

rev1000 does **not** execute recursive String Isomorphism, rerun Johnson reduction, authenticate Git reachability/blobs, infer upstream merge state, reconstruct omitted rev720/rev900 semantics, or convert identity equality into a theorem about facts not represented in the normalized tuple. A false/coercible replay flag, malformed identity, non-shrinking measure, non-power-of-two construction bound, inexact charge, role swap, view mutation, or any shared-field disagreement returns an uncertified result.

This layer is therefore a narrow post-replay compatibility seal, not corrected Split-or-Johnson closure, not GI closure, and not AGI evidence. `agi_state` remains `NOT_AGI`.

## Validation plan

The dedicated smoke compiles the module/test, runs the focused standard-library regression suite, rejects branch-only rev720/rev900 implementation imports, previews canonical `attempt_solution` admission, and enforces the claim's reserved diff. On branch pushes it may materialize only this claim's canonical `attempt_solution` evidence after the functional smoke is green. No sibling workflow is cancelled or manually rerun.
