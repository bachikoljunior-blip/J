# rev3400 — parent-result identity equivalence

Scope: `w1r-h6/corrected-split-or-johnson/larger-ground-recursive-parent-result-identity-equivalence`.

This leaf closes only the explicit identity-equivalence gap retained by the public rev3000/rev3100 chain. The rev3100 coherence object intentionally records `parent_result_identity_equivalence_certified = false`: it proves that the execution proof-DAG and proof/accounting paths carry the same parent-result identity, but it does not independently reconstruct the public rev2200 parent result behind that identity.

rev3400 accepts two independently replay-verified public snapshots: one exact rev2200 parent-filtered result and one rev3100 execution/proof-accounting coherence certificate. It replays both deterministic identities without importing sibling branch-only implementations, validates exact-empty/nonempty coset shape, rechecks the nonempty stabilizer witness family as a finite subgroup, and requires literal equality of the reduction, semantic binding, child instance, child result, parent result, Johnson-ground measure, candidate/accepted counts, and parent-filter work bound. Only then does it set `parent_result_identity_equivalence_certified = true` in a new deterministic certificate.

The certificate establishes that the parent-result identity carried by rev3100 is exactly one independently replayed rev2200 result on the Johnson-ground parent-filter boundary. It does not prove pre-Johnson/original-domain lifting, execute recursive String Isomorphism, modify recurrence/proof-DAG accounting, close corrected Split-or-Johnson or Graph Isomorphism, or establish AGI. State remains `NOT_AGI`.

Parallel boundary: rev3300 / PR #288, rev3100 / PR #287, rev3000 / PR #285, rev2800 / PR #283, rev2707 / PR #280, rev2600 / PR #279, rev2200 / PR #274, shared implementations, `MAIN.md`, claims, branches, PRs, and workflows owned by other executions are read-only and untouched.
