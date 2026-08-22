# AGI-GI rev2800 — parent-filtered proof/accounting coherence

Status: implementation leaf; AGI remains `NOT_AGI`.

## Scope

This revision is owned by claim `chatgpt-session-j-rev2800-soj-parent-filtered-proof-accounting-coherence-20260822T191504JST-2c632434` and scope `w1r-h6/corrected-split-or-johnson/larger-ground-recursive-parent-filtered-proof-accounting-coherence`.

It is a file-disjoint post-replay adapter between two independently owned public-shaped certificates:

- rev2707 parent-filtered result proof-DAG integrity (`PR #280`), and
- rev2600 parent-filtered result recurrence-accounting coherence (`PR #279`).

The adapter imports neither sibling branch-only implementation. It accepts literal serialized snapshots only after explicit independent replay gates, replays the rev2707 proof-DAG digest and canonical lineage/edge shape, replays the rev2600 deterministic accounting-coherence identity, and requires one exact outcome/result/reduction/semantic/child lineage, child-ground measure, candidate count, accepted count, and filtering-work bound across both certificates. It then binds the two distinct upstream identities plus the handoff digest and accounting values into a deterministic SHA-256 coherence identity.

## Fail-closed boundary

The implementation rejects nonliteral container/scalar subclasses, malformed digests, nonliteral replay/certification flags, hidden or missing proof-DAG nodes, edge drift, exact-empty/nonempty drift, identity or measure disagreement, non-strict parent-to-child shrink, negative/non-finite/logical-boolean cost values, top-level schema smuggling, and whole-certificate replay drift.

For nonempty proof snapshots it independently validates the representative and every stabilizer permutation, recomputes witness identities, requires a unique canonically sorted subgroup containing identity and closed under inverse/composition, and checks representative-times-stabilizer injectivity. Schema versions must be exact built-in integers and `reason` fields must be literal built-in strings.

The current hardening additionally reconstructs the exact rev2200/rev2707 parent-result source payload from proof-visible lineage identities, exact-empty/nonempty witness material, action degree, candidate/accepted counts, and filtering work. Its canonical SHA-256 must equal `parent_result_identity`. Therefore an attacker cannot replace the parent-result identity simultaneously in the proof top level, proof-DAG lineage, and accounting certificate and make the forgery pass merely by rehashing both outer certificates. Focused regressions cover this joint-rehash attack for both nonempty and exact-empty outcomes.

`parent_filter_work_bound` and `charged_log2_reduction_cost` remain separate accounting dimensions. rev2800 does not convert or add them, execute recursive String Isomorphism, redo parent filtering, alter shared recurrence/proof-DAG code, or promote either upstream certificate beyond its declared semantics.

## Validation

On implementation head `aeead7010058d987772838465301985dcf883c10`, naturally triggered rev2800 smoke run `32574223677` succeeded. It ran **26/26** focused regressions, `py_compile`, sibling branch-only dependency rejection, and the six-path reservation gate successfully. Fresh canonical `attempt_solution` and `publish` previews against main `f2acbf5683920dab76f58c6825fd7cd68f275261` were both `admitted=true`, `conflicts=[]`; existing canonical phase-evidence files were deliberately left unchanged. Repository-wide Problem-solving parallel admission run `32574223704` and Run-start history integrity run `32574223674` also succeeded on the same implementation head. No workflow was manually rerun or cancelled.

## Integration boundary

rev2707 / PR #280 and rev2600 / PR #279 remain independently owned, open, draft, and unmerged. Downstream rev3000 / PR #285, rev3100 / PR #287, rev3400 / PR #289, homogeneous-block rev3600 / PR #290, signed-Johnson rev3700 / PR #295, and later sibling work remain separately owned and file-disjoint. This leaf therefore remains draft/unmerged until its direct upstream ownership settles.

No sibling claim, branch, PR, workflow, `MAIN.md`, shared recurrence/proof-DAG implementation, or coordination implementation is modified by this revision. No sibling workflow is cancelled or manually rerun, and no sibling branch is rebased or force-pushed.
