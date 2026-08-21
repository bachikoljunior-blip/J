# Parallel-session claims

This directory is the durable, main-visible registry for work that is currently
owned by an independent session.  It prevents two sessions from choosing the
same AGI-GI revision, problem-tree scope, or repository path without depending
on chat memory or a shared local checkout.

## Start protocol

After a scheduled run has written and re-read its mandatory `STARTS.jsonl`
entry, but before any AGI-GI implementation write, every session must:

1. re-read current `main`, open AGI-GI pull requests, and every JSON file here;
2. run `automation/parallel_claims.py check` for the proposed hierarchical
   scope, target revision, and every intended repository path (`--path` may be
   repeated);
3. choose an unclaimed sibling/revision if the check reports a collision;
4. create one schema-v2 JSON file here in a direct `main` commit;
5. re-read `main` and run the check again with its own claim excluded.  This
   second check closes the simultaneous-start race; a newly visible conflicting
   claim requires immediate rescoping before implementation starts.

Example:

```bash
python automation/parallel_claims.py check \
  --scope CRX2/c2b2a2iii2 \
  --target-revision 246 \
  --path automation/solver.py

python automation/parallel_claims.py check \
  --scope CRX2/c2b2a2iii2 \
  --target-revision 246 \
  --exclude-claim-id session-20260821T211000JST-rev246
```

Copy `automation/PARALLEL_SESSION_CLAIM_TEMPLATE.json`, replace every
placeholder, and name the file `<claim_id>.json`.  Timestamps must be ISO 8601
JST values with seconds and the literal `+09:00` offset.  `scope` is a stable
slash-separated problem-tree path, not prose.  A parent and any descendant are
mutually exclusive.  A numeric `target_revision` is also exclusive even when
the scopes differ.  Operational work that consumes no AGI-GI revision uses
`null`. `reserved_paths` may name files or directories, is component-aware,
and is exclusive while fresh; an absolute path or `..` traversal is rejected.

## Heartbeat and close protocol

- Refresh `heartbeat_at_jst` on `main` at least every 30 minutes while making
  durable changes and recheck claims/open PRs before each persistent write.
- A claim is fresh through `stale_after_minutes` after its heartbeat.  The
  canonical value is 90 minutes.
- Stale does not mean safe to overwrite another branch.  Inspect its PR,
  branch, commits, and workflows first, then publish a new takeover/rescope
  claim if needed.
- On merge, abandonment, or supersession, keep the record and change `status`
  to `closed`, `abandoned`, or `superseded`; add `completed_at_jst`.  Closed and
  stale records do not block selection.
- Markdown notices may mirror a claim for humans, but JSON is authoritative.

## Whole problem-solving mechanism

The claim is not only a start marker.  Every recursive phase must run
`automation/problem_solving_parallel_admission.py` against a freshly re-read
main worktree.  Observation phases (`forecast`, `select_leaf`, and
`existing_solution_audit`) may inspect the root but return every other fresh
claim in `parallel_active_claims`.  They must not select another claim's scope.

Mutation/evidence phases (`attempt_solution`, `decompose`, `evaluate`,
`integrate_children`, `solve_parent`, `solve_root`, `update_problem_tree`,
`publish`, and `merge`) are admitted only inside the caller's fresh schema-v2
scope and exact target revision.  A fresh descendant claim blocks parent
integration.  Pass every path the phase will write with repeated `--path`;
each must be inside the caller's `reserved_paths`, and any overlap with another
fresh claim fails closed.  Each result contains the registry source SHA and a digest of all
claims; persist both with the phase evidence so a later session can reconstruct
which parallel work was visible.

Use `--output agi/run-history/phase-admissions/<claim>-<phase>-<time>.json` to
persist an admitted phase.  The pull-request evidence workflow replays that
record from its exact `registry_source_sha`; every problem-state path in the
diff must be covered by the persisted `paths`, so an unreserved write or a
problem-state change without replayable admission fails closed.

Noncanonical records from another worker are never ignored.  A schema-v2
label with a singleton scope list or legacy base fields is loaded as a blocking
interoperability claim: its scope prevents collisions, but it cannot serve as
the caller's canonical owner for an exclusive phase.  Ambiguous multi-scope
records still invalidate the registry.

`automation/parallel_claims.py validate` accepts the historical v1 records in
this directory read-only and enforces the full contract for schema-v2 files.
