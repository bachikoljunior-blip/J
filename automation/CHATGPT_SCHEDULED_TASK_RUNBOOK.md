# ChatGPT Scheduled Task runbook for J

## Purpose

This runbook separates three states that must not be conflated:

1. **repository work result** — code, tests, CI, merge, and persisted problem-tree state;
2. **scheduled-run result** — whether the unattended ChatGPT invocation reached its final response;
3. **schedule-control result** — whether the scheduler could be read or modified after the work.

A failure in (2) or (3) does not erase a verified result in (1). Conversely, a successful notification is not evidence that repository work or AGI criteria succeeded.

The task is not a monitoring-only task. Every invocation must attempt one unresolved AGI-GI leaf or one concrete integration that reduces that leaf. AGI remains `NOT_AGI` until the strict empirical criteria in `MAIN.md` are actually met.

## AGI-GI series scope

`AGI-GI rev series` means the continuous J main revision lineage beginning at rev91 and continuing through whatever revision `MAIN.md` currently records. The graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling / String-Isomorphism work seen in current history describes the **current and historical unresolved branches**, not a permanent domain restriction. A run must follow the current problem tree wherever the AGI root legitimately requires it; if a later unresolved child or transversal solution is outside graph/GI mathematics, it remains part of AGI-GI when it is a continuation of this main lineage.

Separate acceptance/evidence or custodian/federation trees must not be silently counted as AGI-GI revisions unless `MAIN.md` explicitly integrates them into the main lineage. This naming boundary prevents progress-history conflation; it does not narrow the AGI root problem.

## Persistent source of truth

- Repository: `bachikoljunior-blip/J`
- Base branch: `main`
- Main-line state: `MAIN.md`
- Rev-series definition: `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md`
- Rev-series directory: `automation_runs/2026-08-19_0851_JST/`
- Active-node ceiling: the value recorded in `MAIN.md`

A scheduled web run must not assume that a local clone, worktree, uncommitted files, shell process, or prior sandbox survives. It must reconstruct state from the repository on every invocation.

## Invocation contract

At the start of every invocation:

1. Read `MAIN.md` from `main`, read the AGI-GI rev-series definition, and resolve the current main SHA. Treat the latest state in `MAIN.md` as authoritative rather than any revision number embedded in an older prompt or report.
2. After appending and remotely re-reading the mandatory invocation-start record, inspect open AGI-GI pull requests, relevant workflow results, and every JSON claim under `agi/run-history/active/`. The start-history commit remains the first persistent operation of a scheduled run.
3. Select exactly one unresolved active leaf, or one integration shared by several leaves when the active-node ceiling requires a transversal rewrite. Do not restrict selection to graph/GI topics merely because earlier revisions were in that domain. Run `python automation/parallel_claims.py check --scope <canonical/problem/path> --target-revision <rev>` and rescope if it reports a live scope or revision collision.
4. Before any implementation write, publish a unique schema-v2 claim from `automation/PARALLEL_SESSION_CLAIM_TEMPLATE.json` under `agi/run-history/active/<claim_id>.json` in a direct `main` commit. Re-read `main` and repeat the check with `--exclude-claim-id <claim_id>`; this post-commit check detects simultaneous starts. Do not modify, cancel, or rerun work owned by another fresh claim. Follow `agi/run-history/active/README.md` for heartbeat, stale takeover, and close rules.
5. Recheck whether an existing world implementation, theorem, library, solver, oracle, benchmark, or proof framework contains a solution to that leaf and to any ancestor that has not yet received that audit. Record the exact inclusion boundary; do not substitute a name-only literature mention for an integration or proof.
6. Run `automation/problem_solving_parallel_admission.py` for `forecast`, `select_leaf`, and `existing_solution_audit` against the freshly re-read main worktree. Treat `parallel_active_claims` as occupied subtrees; observation may cross them, but selection must not steal or overwrite them.

During repository work:

1. Work on an explicit branch and preserve fail-closed behavior.
2. Re-read claims and open PRs before each persistent write. Refresh the claim heartbeat on `main` at least every 30 minutes; if the scope or revision changes, publish the rescope before touching the new scope.
3. Before every recursive problem-solving transition, run the matching phase admission (`attempt_solution`, `decompose`, `evaluate`, `integrate_children`, `solve_parent`, `solve_root`, `update_problem_tree`, `publish`, or `merge`). Persist its `registry_source_sha` and `registry_digest` with the resulting evidence. A denied phase is not executed; rescope or wait for the conflicting owner instead.
4. Add focused regression tests and connect them to the maintained validation workflow when the change is executable code.
5. Do not call a structural reduction exact unless the returned set/coset is complete and the proof boundary is mechanically checked.
6. Do not claim a quasipolynomial bound unless the recurrence object and every local-cost hypothesis are certified.
7. Do not lower AGI, generality, performance, autonomy, or practical-delivery criteria.
8. Persist a checkpoint before beginning another substantial unit. Consecutive units may be attempted while execution budget remains, but wall-clock busy-waiting is not repository progress.

Before merging:

1. Confirm that the intended head SHA is the SHA tested by CI.
2. Require all relevant workflow jobs to complete successfully.
3. Merge only that verified head.
4. Update `MAIN.md` to the actual merged revision, the verified evidence, the active-node count, and the next unresolved leaf.
5. Leave `AGI = NOT_AGI` unless the independent strict acceptance evidence exists.
6. Close the session claim on `main` after the merge or mark it abandoned/superseded when stopping without integration; retain the record as evidence.

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

> Continue the AGI-GI rev series only in `bachikoljunior-blip/J`. Treat AGI-GI as the continuous main revision lineage from rev91, not as a graph/GI-only scope restriction. Read the latest `MAIN.md` and `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` on `main`, inspect open AGI-GI PRs and CI, and select one unresolved active leaf from the current problem tree regardless of technical domain. Attempt a concrete implementation or proof-carrying integration; audit existing world solutions for that leaf and unaudited ancestors; preserve exactness and fail-closed gates; add tests; merge only a CI-verified head; update `MAIN.md` with the verified result and next leaf. Do not treat this as monitoring, do not lower AGI criteria, and do not claim AGI without strict empirical evidence. Persist durable checkpoints before proceeding to another unit. Do not modify this scheduled task from inside the run. Distinguish repository success from notification or scheduler-aftercare failure.

The long root constraint remains authoritative as the session-level problem definition. This shorter invocation prompt is an execution protocol, not a relaxation of the root or AGI criteria.
