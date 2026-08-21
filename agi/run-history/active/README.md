# Parallel-session claims

This directory is the durable, main-visible registry for work that is currently
owned by an independent session.  It prevents two sessions from choosing the
same AGI-GI revision or the same problem-tree scope without depending on chat
memory or a shared local checkout.

## Start protocol

After a scheduled run has written and re-read its mandatory `STARTS.jsonl`
entry, but before any AGI-GI implementation write, every session must:

1. re-read current `main`, open AGI-GI pull requests, and every JSON file here;
2. run `automation/parallel_claims.py check` for the proposed hierarchical
   scope and target revision;
3. choose an unclaimed sibling/revision if the check reports a collision;
4. create one schema-v2 JSON file here in a direct `main` commit;
5. re-read `main` and run the check again with its own claim excluded.  This
   second check closes the simultaneous-start race; a newly visible conflicting
   claim requires immediate rescoping before implementation starts.

Example:

```bash
python automation/parallel_claims.py check \
  --scope CRX2/c2b2a2iii2 \
  --target-revision 246

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
`null`.

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

`automation/parallel_claims.py validate` accepts the historical v1 records in
this directory read-only and enforces the full contract for schema-v2 files.
