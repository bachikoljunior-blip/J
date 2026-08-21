# rev251 — exact result replay verifier

## Scope

This revision adds an isolated, bounded verifier for exact String-Isomorphism
results over an **explicitly enumerated finite permutation group**.  It does
not edit or call the shared CRX1/CRX2 solvers.

The verifier snapshots source/target colors, validates the candidate
enumeration as a finite permutation group, replays every candidate, compares
the complete replayed transporter set with the claimed result, and checks the
target-stabilizer coset reconstruction for every non-empty result.

## Fail-closed boundaries

The verifier returns no exact acceptance when:

- the producer status is not `exact`;
- the candidate enumeration is malformed, duplicated, or not a group;
- the claimed result is not a subset of the candidate group;
- the certificate digest does not match;
- the replayed result differs from the claimed complete set; or
- any degree, group-size, composition, action-check, or certificate-size cap
  is exceeded.

An over-cap result is `unknown_resource_cap`, never a guessed acceptance.

Exactness is relative to the supplied explicit candidate group.  This
component intentionally does not claim that the supplied group equals a
larger ambient group; that obligation remains with the upstream producer.

## Verification

```bash
python -m unittest \
  automation_runs/2026-08-19_0851_JST/test_exact_result_replay_verifier_rev251.py
```

The regression suite covers non-empty and empty exact results, target
stabilizer/coset size, omitted transporters, malformed non-groups, non-exact
producer status, preflight resource caps, digest tampering, mutable-input
snapshot isolation, order-stable digests, and duplicate candidate rejection.

## Parallel-execution boundary

Reserved files:

- `exact_result_replay_verifier_v1.py`
- `test_exact_result_replay_verifier_rev251.py`
- `REV251_EXACT_RESULT_REPLAY_VERIFIER.md`

No existing solver, workflow, claim, or `MAIN.md` file is modified.  The
session marker is
`agi/run-history/active/chatgpt-session-j-rev251-20260821T221010JST-27c9422d.json`.
The main-branch hourly watchdog (`17 * * * *`) observes active-claim commits
and emits a durable continuation request when repository execution becomes
idle.
