# rev340 — corrected SOJ Johnson recursive-result/accounting binding

Status: implementation leaf only; NOT_AGI.

## Boundary

This revision adds one file-disjoint post-recursion cross-certificate for the larger-ground Johnson branch. It does not construct the Johnson relational reduction, execute recursive String Isomorphism, change the recurrence validator, or import branch-only sibling modules.

The caller must independently replay both sibling contracts before invoking this adapter:

- a rev291-style `certified_corrected_soj_larger_ground_recursive_handoff`, which proves that the represented Johnson action has been admitted as one exact/canonical, cost-certified `aux_shrink` recurrence edge to its Johnson ground; and
- a rev293-style exact recursive child result lift, either `certified_exact_parent_johnson_coset_lift` or `certified_exact_empty_parent_johnson_result`.

The adapter then fail-closes unless the two independently replayed certificates agree on the exact reduction identity, represented parent action degree, and Johnson child-ground measure. It also rechecks the retained handoff recurrence shape (canonical/cost-certified `aux_shrink`, one multiplicity-one child, certified recurrence validation) and preserves exact-empty versus nonempty result semantics. Nonempty lifted results must carry a syntactically valid parent permutation and canonical generator sequence; semantic transport remains the upstream rev293 replay obligation.

A successful result is a deterministic `certified_johnson_recursive_result_accounting_binding` with a replay-stable SHA-256 binding digest over the shared reduction identity, handoff digest, child-result identity, result-lift digest, represented measures, outcome kind, and charged logarithmic reduction cost.

## Non-interference

Only rev340 reserved paths are changed. rev275–rev320 sibling claims/branches/PRs/workflows, including rev291, rev292, rev293, rev295, and rev320, are read-only. `MAIN.md`, CRX1/CRX2/CRX3 implementation paths, shared proof-DAG code, recurrence-accounting code, and shared coordination implementation are untouched.

## Validation

The implementation and focused test module compile successfully. The first dedicated PR smoke exposed only an environment assumption: the hosted Python image did not include `pytest`. The rev340 workflow was therefore made dependency-free and now discovers and executes the plain-assert focused tests with the standard library; the corrected dedicated smoke passed compile, focused regression, sibling-import rejection, and reserved-path enforcement.

After the corrected push smoke was green, the workflow invoked the repository's authoritative `automation/problem_solving_parallel_admission.py` against the exact rev340 claim/scope/paths. The generator admitted `attempt_solution` with `conflicts=[]` and committed the generated payload at the reserved phase-admission path. No admission payload was hand-authored or inferred from stale state.

A connector-authored follow-up documentation commit intentionally follows the bot evidence commit so pull-request checks are evaluated on an ordinary branch head containing that exact generated evidence. The repository-wide phase-evidence guard remains authoritative for the final head.
