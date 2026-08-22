# REV900 — recursive production provenance / total-cost binding

## Scope

This revision owns only
`w1r-h6/corrected-split-or-johnson/larger-ground-recursive-production-provenance-total-cost-binding`
under durable claim
`chatgpt-session-j-rev900-soj-recursive-production-provenance-total-cost-20260822T144656JST-c1d9bf7e`.

It is a downstream, file-disjoint compatibility leaf. It does not modify or import the branch-only implementations owned by rev700 / PR #251, rev720, or rev800 / PR #252.

## Contract being checked

rev700 publishes a deterministic recursive-production provenance identity tying together the caller replay envelope, main provenance, recursive producer provenance, result lift, accounting binding, reduction identity, and child-result identity. rev800 publishes a deterministic total-cost coherence identity tying the recursive accounting binding to the Johnson construction-cost binding and requiring the construction charge to occur exactly once.

rev900 accepts only when both upstream output certificates have been independently replay-verified and their compact deterministic output identities replay locally. It then requires:

- identical `accounting_binding_digest` values;
- identical `reduction_identity` values;
- compatible exact-empty/nonempty semantics (`exact_nonempty` ↔ `nonempty`, `exact_empty` ↔ `exact_empty`);
- a positive strict recursive shrink from the rev800 certificate;
- an integral power-of-two construction-cost bound;
- `charged_log2_reduction_cost == log2(construction_multiplicative_cost_bound)` exactly.

The accepted payload preserves the rev700 provenance identities and rev800 cost/coherence identities and seals them into a separate deterministic `sha256:` `total_cost_binding_identity`.

## Fail-closed boundary

Identity replay here is not a substitute for omitted semantics. rev900 does **not**:

- execute recursive String Isomorphism;
- reconstruct the Johnson relational reduction or its solution transport;
- perform Git reachability/blob authentication owned by the provenance leaves;
- infer that rev700, rev720, or rev800 is merged;
- import branch-only sibling modules;
- modify shared recurrence/accounting code;
- claim corrected Split-or-Johnson, GI, or AGI closure.

The two explicit upstream replay gates remain mandatory because those upstream certificates summarize noncompact checks that cannot be reconstructed from the compact outputs alone.

## Validation

Before publication, the rev900 module and focused test file were syntax-compiled locally and the fail-closed regression suite passed 16/16 cases. The suite covers successful nonempty and exact-empty bindings, replay round trips, both replay gates, accounting/reduction mismatch, semantic mismatch, deterministic-identity drift, non-power-of-two cost, incorrect log charge, boolean coercion, malformed digest encoding, invalid recursive measure, contract-status drift, and deterministic output sensitivity.

The dedicated branch workflow repeats compile and focused regression checks, rejects sibling implementation imports, previews canonical `attempt_solution` admission, enforces the reserved diff, and materializes only this claim's canonical attempt-solution evidence on its own branch after a green push smoke.

`agi_state` remains `NOT_AGI`.
