# AGI-GI rev265: implicit relation-image original-root resource envelope

## Scope

This revision restores the collision-free resource-accounting leaf previously validated on superseded rev258 / PR #199. Fresh coordination showed that rev258 and then rev264 had been acquired by parallel sessions, so this session closed its old claim without merge and moved the same sibling leaf to rev265. It does not modify any active exact image-coset, paired-preimage, parent-promotion, primitive-Johnson, or CRX3 implementation file.

## Phase admission

Before the implementation write, the branch generated and persisted an exact `attempt_solution` admission record from repository commit `ae4553da541b02dae5f76b4486f789c221c9b16c`. The record is replayable by `automation/problem_solving_phase_evidence_guard.py` and covers every rev265 problem-state path. Its registry snapshot includes the then-fresh rev252, rev260, rev261, rev262, rev263, rev264 and CRX3 claims and reports no collision.

## Contract

Before constructing an exact implicit relation-image group, `implicit_relation_image_resource_envelope_v2.py` reserves one complete bounded attempt covering induced auxiliary-generator construction, implicit domain and image Schreier work, complete value-preserving auxiliary-coset intersection below an original-root polynomial image-order gate, paired original-domain preimage reconstruction, and final exact transport/containment verification.

All arithmetic saturates only at `max_work + 1` using Python arbitrary-precision integers. Because `image_order_upper_bound` is only an upper bound, the resource proof does not divide the domain-order upper bound by it to estimate a kernel. Such a division can under-reserve. The conservative kernel reservation is the full domain-order upper bound.

Admission requires the domain degree to fit the original root, the auxiliary degree to fit the explicit quadratic lift gate, the image-order bound to fit `min(max_image_order, root ** image_order_poly_power)`, and the aggregate bound to fit `max_work`.

Rev265 additionally exposes the immutable six-part `phase_work_upper_bounds` split. This lets a later execution-linked consumer bind induced action, both Schreier phases, value-coset intersection, paired preimage and final verification to exactly the same pre-execution reservation rather than reconstructing phase costs independently.

## Strict boundary

`admitted=True` is a finite pre-execution resource statement only. `complete` remains false. This revision does not implement the exact value-coset intersection, does not lift a concrete intersection back to the original domain, does not promote the parent result, and does not claim GI or AGI. Those execution obligations remain separate sibling leaves.

## Parallel safety

The authoritative claim is `chatgpt-session-j-rev265-resource-envelope-20260822T074900JST-f3389aa0`. The branch uses only five reserved rev265 paths, including its phase-admission evidence. Superseded PR #199 is closed and preserved unchanged as audit history. Sibling PRs/branches/claims/workflows are not cancelled, modified, or rerun.

## Validation target

The focused suite contains 12 regressions: the 11 previously green rev258 resource tests plus a rev265 check that the explicit six-phase split exactly sums to the unsaturated aggregate reservation on the reference case. The dedicated workflow also compiles the module and tests, and the repository-wide Problem-solving parallel admission workflow replays the persisted evidence against its source registry commit.
