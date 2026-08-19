# ChatGPT Scheduled Task runbook for J

## Purpose

This runbook separates three states that must not be conflated:

1. **repository work result** — code, tests, CI, merge, and persisted problem-tree state;
2. **scheduled-run result** — whether the unattended ChatGPT invocation reached its final response;
3. **schedule-control result** — whether the scheduler could be read or modified after the work.

A failure in (2) or (3) does not erase a verified result in (1). Conversely, a successful notification is not evidence that repository work or AGI criteria succeeded.

The task is not a monitoring-only task. Every invocation must attempt one unresolved AGI-GI leaf or one concrete integration that reduces that leaf. AGI remains `NOT_AGI` until the strict empirical criteria in `MAIN.md` are actually met.

## Persistent source of truth

- Repository: `bachikoljunior-blip/J`
- Base branch: `main`
- Main-line state: `MAIN.md`
- Rev-series directory: `automation_runs/2026-08-19_0851_JST/`
- Active-node ceiling: the value recorded in `MAIN.md`

A scheduled web run must not assume that a local clone, worktree, uncommitted files, shell process, or prior sandbox survives. It must reconstruct state from the repository on every invocation.

## Invocation contract

At the start of every invocation:

1. Read `MAIN.md` from `main` and resolve the current main SHA.
2. Inspect open AGI-GI pull requests and relevant workflow results so that already-completed work is not repeated.
3. Select exactly one unresolved active leaf, or one integration shared by several leaves when the active-node ceiling requires a transversal rewrite.
4. Recheck whether an existing world implementation, theorem, library, solver, oracle, benchmark, or proof framework contains a solution to that leaf and to any ancestor that has not yet received that audit. Record the exact inclusion boundary; do not substitute a name-only literature mention for an integration or proof.

During repository work:

1. Work on an explicit branch and preserve fail-closed behavior.
2. Add focused regression tests and connect them to the maintained validation workflow when the change is executable code.
3. Do not call a structural reduction exact unless the returned set/coset is complete and the proof boundary is mechanically checked.
4. Do not claim a quasipolynomial bound unless the recurrence object and every local-cost hypothesis are certified.
5. Do not lower AGI, generality, performance, autonomy, or practical-delivery criteria.
6. Persist a checkpoint before beginning another substantial unit. Consecutive units may be attempted while execution budget remains, but wall-clock busy-waiting is not repository progress.

Before merging:

1. Confirm that the intended head SHA is the SHA tested by CI.
2. Require all relevant workflow jobs to complete successfully.
3. Merge only that verified head.
4. Update `MAIN.md` to the actual merged revision, the verified evidence, the active-node count, and the next unresolved leaf.
5. Leave `AGI = NOT_AGI` unless the independent strict acceptance evidence exists.

## Failure classification

Report one of these states explicitly:

- `REPO_SUCCESS_RUN_SUCCESS`: verified repository result and normal scheduled response.
- `REPO_SUCCESS_RUN_AFTERCARE_FAILED`: verified repository result exists, but notification, schedule control, final summarization, or another aftercare action failed.
- `REPO_PARTIAL`: a branch, PR, test result, or other durable checkpoint exists, but the selected leaf is not integrated.
- `REPO_NO_CHANGE_BLOCKED`: no durable repository change; state the exact failing permission, unavailable tool, CI error, theorem gate, or reproducible technical blocker.

Never report “not executed” merely because the last aftercare action failed. Cite the durable commit, PR, workflow, or file that proves what did execute.

## Schedule-control boundary

The recurring task must **not attempt to enable, recreate, pause, resume, or rewrite itself from inside the unattended run**. Scheduler control is an external control-plane operation and may be unavailable even when GitHub work succeeds. The schedule should be kept enabled outside the per-run prompt until AGI is strictly achieved; an unavailable schedule-control tool is not a reason to mark verified repository work failed.

The per-run prompt may verify scheduler state only when a scheduler-read capability is actually present. It must not turn absence of that capability into an algorithmic failure or fabricate that the schedule was enabled.

## Recommended durable per-run prompt

> Continue the AGI-GI rev series only in `bachikoljunior-blip/J`. Read `MAIN.md` on `main`, inspect open AGI-GI PRs and CI, and select one unresolved active leaf. Attempt a concrete implementation or proof-carrying integration; audit existing world solutions for that leaf and unaudited ancestors; preserve exactness and fail-closed gates; add tests; merge only a CI-verified head; update `MAIN.md` with the verified result and next leaf. Do not treat this as monitoring, do not lower AGI criteria, and do not claim AGI without strict empirical evidence. Persist durable checkpoints before proceeding to another unit. Do not modify this scheduled task from inside the run. Distinguish repository success from notification or scheduler-aftercare failure.

The long root constraint remains authoritative as the session-level problem definition. This shorter invocation prompt is an execution protocol, not a relaxation of the root or AGI criteria.
