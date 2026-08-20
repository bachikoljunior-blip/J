# AGI-GI rev207 problem-tree audit

## Starting canonical leaf

`H6-C1` from main after rev206: connect the complete exact parent Design union and its exact-empty / strict-progress evidence to proof-carrying downstream SI and charge the quadratic coupled auxiliary action, branch multiplicity, Design work, and union reconstruction without manufacturing a global W1R-H6 closure.

Problem-count prediction remains **512** and the non-replaced effective count remains **512**.  The actual count has not exceeded the prediction, so the mandatory over-count full-tree rewrite trigger does not fire in this revision.

## World-solution inclusion audit

The relevant outside solution layer was rechecked against László Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547, and Babai's January 2017 corrected Split-or-Johnson update.  Those sources explicitly place String Isomorphism and Coset Intersection inside the same quasipolynomial group-action framework and repair the recursive Split-or-Johnson analysis rather than replacing exact group/coset recursion with an unrelated solver.

For the rev206 boundary this suggests a higher-level simplification: an auxiliary action of polynomial degree does not need to become a new independent primary problem merely because its degree is larger than the parent permutation domain.  If the actual auxiliary SI invocation already returns a self-contained proof-carrying quasipolynomial recurrence certificate and its degree is mechanically bounded by a fixed polynomial in the original root measure, its certified work can be translated back to the original root's polylogarithmic exponent.  The exact coupled bipartite auxiliary action satisfies

`M = |L| + |R| + |L||R| <= root_n + root_n^2`

because `L` and `R` are disjoint subsets of the parent domain.

## Cross-cutting replacement

rev206 deliberately separated strict Design shrink from downstream exact SI and therefore emitted placeholder children in `bipartite_design_recurrence_gate_v1`.  rev207 does **not** pretend those placeholders are solved.  Instead it notices that every branch for which rev206 actually returned an exact parent result already executed `candidate_coset_string_isomorphism_u2`, whose exact result carries a recurrence accounting tree.

`bipartite_parent_polynomial_lift_accounting_v1` therefore:

1. recomputes the same complete rev206 parent union;
2. replays the same paired parent-to-right preimage and coupled auxiliary action for each materialized structural branch;
3. replays the exact candidate-coset SI and validates its accounting tree with the existing v3 verifier;
4. checks `M <= root_n + root_n^2` for every branch;
5. charges actual branch multiplicity, the Design structural local bound, rev206 union bookkeeping, and a separate fixed-degree polynomial wrapper envelope;
6. accepts only if the composed numeric work bound lies inside a fixed quasipolynomial envelope in the original root.

This removes an unnecessary branch of the problem tree **for exact rev206 instances**: they no longer need an artificial structural-child recursion solely to explain the quadratic auxiliary action.  It does not remove the genuinely unresolved candidate-SI cases.  If rev206 itself fails closed, rev207 also fails closed before any cost claim.

## New boundary

If validation succeeds, `H6-C1` is replaced in place by the narrower leaf:

**H6-C2:** extend exact proof-carrying candidate SI to the rev206 image branches that still return typed unresolved primitive-giant / higher-arity Johnson / full Split-or-Johnson states, so the complete parent union becomes exact on those inputs as well.  Preserve actual parent coupling and the polynomial-lift accounting invariant; resource caps and unresolved candidate proofs remain fail closed.

This is not full W1R-H6 closure and is not AGI evidence.  AGI remains **NOT_AGI**.
