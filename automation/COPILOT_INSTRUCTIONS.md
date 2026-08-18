# Hourly AGI run — execution instructions

These instructions describe the isolated runner environment. The user's Japanese prompt is supplied separately and unchanged.

- Work only with the material in this temporary workspace. `context/J/` is a snapshot of the J repository at the start of this run. Do not use or assume any other repository, codebase, progress, or result.
- Treat existing material as evidence, not as automatically true. Preserve failures and uncertainty. Never claim that a test, implementation, benchmark, integration, or deployment occurred unless you actually performed it in this run or can cite concrete evidence in `context/J/`.
- Read the latest relevant files under `context/J/runs/` before selecting the next unresolved leaf. Continue from the strongest verifiable state rather than restarting or duplicating solved branches.
- Put every new deliverable under `artifacts/`. You may create code, tests, datasets, logs, reports, and machine-readable state there. Do not edit `context/`.
- Prefer executable, falsifiable work. Run tests or evaluations when feasible and retain stdout, stderr, exit codes, and failed cases. Keep AGI candidate artifacts distinct from the problem-solving process and its bookkeeping.
- Before ending, run `TZ=Asia/Tokyo date '+%Y-%m-%dT%H:%M:%S%z minute=%M'`. If the minute is less than 55, continue with the next concrete task. Do not wait idly merely to reach minute 55.
- Before the final response, ensure these files exist under `artifacts/`:
  - `RUN_SUMMARY.md`: work attempted, evidence, tests, failures, next unresolved leaf, and certification status.
  - `CURRENT_STATUS.json`: machine-readable current root/problem-tree/certification state.
  - `PROBLEM_DELTA.json`: selected leaf, attempted solution, result, decomposition or integration changes, and revised counts.
- Certification is fail-closed: unless strict empirical evidence establishes the full root criterion in a practically deliverable form, record `root_problem_solved: false` and `agi_certified: false`.
