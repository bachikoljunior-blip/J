# Run-start history canonical revision integrity

## Observation

STARTS.jsonl is append-only, but before this change no independent guard
replayed every immutable starting_main_sha. A stale declared revision could
therefore survive unless a human noticed it and appended a correction.

## Existing-world solution audit

This change composes mechanisms already present in J:

- canonical AGI-GI revN parsing from agi_gi_main_revision_guard.py;
- exact starting-ref resolution from agi_gi_run_start_record.py;
- Git reachability for immutable historical main SHAs;
- explicit append-only automation_run_start_correction events.

No new definition of an integrated revision is introduced.

## Attempt

The guard validates JSONL structure, unique run IDs, correction lineage, JST
timestamps, and the canonical maximum revision reachable from each start SHA.
A mismatch is accepted only when one correction binds the same run, start SHA,
start timestamp, superseded revision, corrected revision, and canonical
evidence commit. Everything else fails closed.

Historical starts written before ancestry-derived recording are counted as
legacy-unverifiable. The first record carrying an ancestry-derived source or
integration-commit identity starts permanent enforcement: every later start is
replayed even if its marker is missing. Explicit legacy corrections are also
replayed, so the enforcement boundary cannot move forward silently.

## Boundary

This closes a repository-coordination integrity leaf only. It is not an AGI
capability result. The strict status remains NOT_AGI.
