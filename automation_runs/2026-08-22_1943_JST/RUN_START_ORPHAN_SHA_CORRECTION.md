# Run-start orphan SHA correction

## Observed failure

The independent run-start history workflow failed after its unit tests passed because start record `chatgpt-session-j-continuation-20260822T184632+0900-34c9ca6e-turn4` named `34c9ca6eafc11a0737fbacb70fd0fc244bea6973`, which GitHub and `git rev-parse` cannot resolve.

## Evidence and correction

The original JSONL line remains unchanged. A new append-only `automation_run_start_identity_correction` event binds the same run id, timestamp, original SHA, recorded revision, corrected SHA, and next-main SHA. Reachable main commits provide an exact first-parent bracket:

- corrected start commit `34c2440682b1f6af6d1fc78e7805ff4a656f8d06`, committed at 2026-08-22T18:46:13+09:00;
- next main commit `bf47653ff17b50d1f5f405d43a5c6929a491aa79`, committed at 2026-08-22T18:46:53+09:00, whose sole parent is the corrected commit;
- immutable start timestamp 2026-08-22T18:46:32+09:00 lies inside that interval;
- corrected-start ancestry resolves to canonical AGI-GI rev1600 evidence commit `9606bf7711bfab4bb54ad1ddff315420b75a561d`.

The guard now accepts an identity correction only when it is unique, binds every immutable start field, resolves both commits exactly, proves the next commit's sole parent is the corrected commit, proves the next commit is reachable from the validation HEAD, and proves the start timestamp is bracketed by their committer times. Missing, duplicate, malformed, unbound, non-ancestral, or non-bracketing evidence fails closed.

This is repository coordination integrity only. It does not implement String Isomorphism, Graph Isomorphism, or AGI; status remains `NOT_AGI`.
