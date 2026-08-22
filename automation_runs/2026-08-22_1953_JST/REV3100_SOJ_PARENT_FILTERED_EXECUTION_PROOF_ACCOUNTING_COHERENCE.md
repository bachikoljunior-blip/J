# rev3100 — parent-filtered execution / proof-accounting coherence

## Scope

This leaf is a file-disjoint post-replay adapter between the public rev3000 parent-filtered child-execution proof-DAG binding and the public rev2800 parent-filtered proof/accounting coherence certificate. It was re-homed from the retired rev2900 attempt after the independent rev2500 owner correctly moved that upstream contract to fresh-main rev3000.

## Certified boundary

The adapter independently validates literal public-shaped snapshots and requires replay evidence to be literal `True`. It replays the rev3000 binding identity and rev2800 coherence identity, then requires the same parent-filtered result identity, reduction identity, child-result identity, parent outcome, and child-ground measure across both certificates.

The child execution outcome remains a distinct field from the post-filter parent outcome: a nonempty child execution may still produce an exact-empty parent result after exact parent filtering. An exact-empty child execution may bind only to an exact-empty parent result. The adapter preserves rev3000's `same_child_execution_certified=true` while requiring `parent_result_identity_equivalence_certified=false`; it does not manufacture equality between independently defined parent-result certificates.

Proof-DAG identities, execution closure/lift/proof identities, recurrence-accounting identity, handoff identity, filtering work, and charged reduction cost remain separately exposed. Unlike accounting units are not combined. Strict parent-to-child shrink and exact-empty/nonempty count invariants are fail-closed.

## Parallel safety

No rev3000, rev2800, rev2707, rev2600, rev2200, rev1400, run-start-history, coordination, `MAIN.md`, or sibling implementation path is modified or imported. The implementation uses only public-shaped snapshots and the Python standard library. Unrelated workflows are not cancelled or manually rerun.

## Validation

The focused suite contains 18 regressions covering nonempty and exact-empty success paths, post-filter empty after a nonempty child execution, deterministic replay, literal replay gates, subclass rejection, digest tampering, cross-certificate lineage drift, outcome/source-status drift, strict shrink, accounting-cost validation, and output mutation. Local execution: 18/18 passed; `py_compile` passed.

This leaf is not a proof of corrected Split-or-Johnson closure, GI completion, or AGI. State remains `NOT_AGI`. Keep it draft/unmerged while rev3000 and rev2800 are independently owned and unmerged.
