# AGI-GI rev211 problem-tree audit

## Count and trigger

The forecast remains **512** and the effective non-replaced count remains **512**. The actual count has not exceeded the forecast, so the mandatory over-count rewrite trigger does not fire. rev211 replaces unresolved primitive/Johnson subleaves in place; it does not add a parallel solver family.

## Existing-solution audit at the parent layer

The current candidate dispatcher already contains several pieces of the quasipolynomial SI architecture, but they entered the repository at different times. The important cross-layer observation is that a large Johnson point domain does not imply that the represented signed-ground group is large. rev175 gives a faithful exact lift to the smaller signed ground, and rev176 can enumerate that represented group when its order is polynomially bounded even when the Johnson point domain is above the legacy explicit ground cap. This is a direct reuse of exact permutation-group/coset structure rather than another combinatorial branch.

For larger represented signed groups, rev184 provides a separate canonical continuation: a complete O(log n)-arity complement-safe relation, incidence/codegree descent, exact source/target invariant mismatches, exact signed-partition transport for significant splits, and an explicitly fail-closed homogeneous Design remainder. Later rev185-rev195 strengthened the Design hypothesis/conclusion and recurrence proof machinery, but rev184's exact terminal/filter outcomes were never wired back into this candidate boundary.

Therefore rev211 reuses rev176 first and rev184 second after rev209 has already exhausted joint relation, adaptive relation and exact profile terminals. It does not promote rev184 structural evidence into an exact SI result: only `exact=True` results are translated through the candidate representative. If rev176 proves that no exact Johnson lift exists, rev184's identical bounded recognizer is not repeated.

## Direct attempt

The focused PGL(2,8) action on J(9,2) has degree 36 and represented group order 504. With the old candidate caps forced below both the Johnson ground and generic group-enumeration thresholds, candidate-v3 remains nonexact. rev211 uses the faithful signed-ground lift and a dedicated polynomially bounded signed-group cap to reconstruct the exact full relation coset. Tests cover a positive transporter, a nontrivial right-coset representative, and an exact-empty equal-inventory target.

The focused smoke also reruns rev184's logarithmic relation/Design regression so that the second continuation substrate stays mechanically validated even when a particular rev211 fixture closes at the stronger rev176 terminal first.

## Branch deletion and next boundary

On successful validation, polynomial-order signed-ground Johnson candidates no longer belong to the unresolved large-ground branch. The remaining primitive/Johnson frontier is restricted to larger represented signed groups for which joint/adaptive/profile exact routes do not close. rev184 can still produce exact mismatch or split/candidate outcomes there; its nonexact homogeneous Design or second-Johnson structural outputs require a later proof-carrying composition with the strengthened rev185-rev195 Design machinery.

True nonliteral giant quotients, primitive non-Johnson states, and the rest of corrected Split-or-Johnson recursion also remain unresolved. Full W1R-H6, global quasipolynomial closure, and AGI are not claimed. AGI remains **NOT_AGI**.
