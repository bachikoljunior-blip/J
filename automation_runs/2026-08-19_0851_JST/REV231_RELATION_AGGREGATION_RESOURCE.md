# AGI-GI rev231 — canonical relation aggregation resource envelope

rev231 decomposes the remaining original-root consumer leaf into canonical
relation aggregation, correlated t-WL, and Design/transport work.  It resolves
the first subleaf by preflighting the complete Boolean-incidence refinement with
the exact `C(m,t)` multiplicity and a conservative bound for every possible
refinement round.  Rejected work is not started; admitted execution records the
actual round count and a conservative charged upper bound.

This includes WCET/admission-control accounting and the standard finite
partition-refinement termination bound.  It is not promoted to a bound for t-WL,
Design branching, transport, or full-string SI, which remain explicit leaves.

The former one leaf is replaced by its parent plus three children, so the active
problem count becomes `537 - 1 + 4 = 540`, below the forecast 576.  The
over-count rewrite trigger therefore does not fire and no child is suppressed.

AGI status remains `NOT_AGI`.
