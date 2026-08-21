# REV254 — Design primitive-Johnson complete-cover preflight

## Boundary

rev243 reserved an input-independent primitive-non-giant Johnson/profile resource envelope, and rev246 attached that reservation to an executable signed-Johnson/profile attempt. rev246 deliberately stopped before the shared Design caller because PR #177 owns the adjacent rev245 Design/imprimitive integration paths.

rev254 closes the standalone part of that remaining boundary without touching any shared caller file. It adds a complete-cover adapter that a later caller can feed exactly the branch indices not already owned by cheaper terminals.

## Contract

`design_primitive_johnson_complete_cover_preflight` runs before any rev246 execution. For every caller-selected branch it:

- requires the exact S1 classifier to certify canonical `primitive_non_giant`;
- instantiates the rev243 resource envelope from the exact currently known branch subgroup order and generator count;
- keeps the original root degree explicit and includes the envelope's paired image/kernel/preimage lift charge;
- sums every selected branch's full reservation with `cap + 1` saturation under one caller-supplied finite cap;
- rejects the entire selected subcover if any selected branch is not primitive-non-giant, lacks an admitted envelope, loses original-root lift, or makes the aggregate cap overflow.

No selected branch is executed by this module. Non-selected branches remain the caller's responsibility and are charged elsewhere.

`record_design_primitive_johnson_complete_cover_execution` then binds ordered rev246 results back to the immutable reservations. It rejects a result that loses production admission, changes the root/current/image degree, enlarges any reserved order/generator/partition/lift/work bound, escapes the reserved Johnson parameter family, overcharges its branch reservation, or omits a selected branch while claiming complete execution.

This supplies the missing complete-cover selection plus execution-linked original-root charge substrate. It does **not** modify the shared Design U2/full-string caller, so final caller wiring remains a separate collision-sensitive integration after PR #177 settles.

## Parallel safety

The implementation is four new rev254 paths only:

- `design_primitive_johnson_complete_cover_preflight_v1.py`
- `test_design_primitive_johnson_complete_cover_rev254.py`
- this audit note
- `.github/workflows/rev254-design-primitive-johnson-complete-cover-smoke.yml`

The durable claim is `chatgpt-session-j-rev254-20260821T231757JST-08e81c38`. The branch does not modify PR #177's six shared Design paths, any rev247–rev253 reserved path, `MAIN.md`, another claim, another branch/PR, or an existing workflow.

## Remaining boundary

After rev254, the primitive-Johnson leaf still needs one shared-caller integration step: combine the settled Design terminal preflight with rev254's selected primitive-Johnson subcover, pass the per-branch reservation into the rev246 operator, and record the resulting charge in the caller's original-root ledger before exact union reconstruction. That step must not be attempted while the active rev245 shared caller work remains unsettled.

AGI state remains `NOT_AGI`.
