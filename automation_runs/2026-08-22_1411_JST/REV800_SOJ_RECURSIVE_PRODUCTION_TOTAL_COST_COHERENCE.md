# Rev800 — recursive production total-cost coherence

## Scope

This file-disjoint leaf checks one narrow accounting boundary between the public rev340 recursive-result/accounting binding contract and this session's public rev360 Johnson construction-cost binding contract. It does not import either sibling implementation and it does not execute recursive String Isomorphism, reconstruct the Johnson relational reduction, inspect Git provenance, or modify shared recurrence/proof-DAG code.

The adapter requires both source objects to have been mechanically replayed by their owners/callers. It then independently recomputes the deterministic digest exposed by each schema, requires the same Johnson reduction identity, parent action degree, and recursive child ground, and checks the unit conversion that matters for recurrence accounting: rev360's conservative multiplicative construction bound must be an integral power of two and rev340's `charged_log2_reduction_cost` must equal its exact base-2 logarithm.

That equality is deliberately an exact-once condition. Rev340's charge belongs to the already-admitted recursive handoff edge, so adding rev360's construction charge again in this adapter would double count construction work. A lower charge would omit certified work. Either mismatch fails closed.

## Strict boundaries

The output is only a deterministic cross-certificate coherence identity. It preserves rev340's `exact_empty` versus `nonempty` outcome distinction, accepts no coercible booleans, rejects malformed/noncanonical digests, rejects measure or reduction-identity drift, and does not claim that any sibling PR is merged or semantically complete beyond the supplied replay gates.

## Verification

Before publication, the standalone module and regression file were compiled successfully and the focused suite passed 13/13 cases. The dedicated workflow repeats compile/regression checks, rejects imports of branch-only rev340/rev360 implementations, previews canonical phase admission, enforces the reserved-path diff, and on branch push materializes only this claim's canonical `attempt_solution` evidence after the smoke steps are green.

`agi_state` remains `NOT_AGI`; this is one accounting-coherence leaf, not corrected Split-or-Johnson/GI/AGI closure.
