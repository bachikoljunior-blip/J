# main integrated-revision guard audit

## Observed defect

Multiple independent branches merged in the order rev244, rev242, rev243 while
`MAIN.md` still declared rev241.  All three canonical integration commits were
reachable from `main`; therefore wall-clock merge order and the last branch that
edited documentation were not sufficient to identify the numeric continuation
point.  No unmerged rev245 or rev246 result is counted here.

## Implemented boundary

`automation/agi_gi_main_revision_guard.py` reads only commits reachable from the
requested Git ref and recognizes only subjects beginning with the reserved
integration prefix `AGI-GI revN:`.  It computes the numeric maximum and requires
the single canonical sentence in `MAIN.md` to match exactly.  The check fails
closed when either evidence source is absent or when MAIN is behind or ahead.

This incorporates established release-ledger and Git-reachability practice:
monotone numeric state is derived from immutable reachable integration events,
not from branch names, claims, prose, PR state, or commit arrival order.  A
separate static ledger would create a second stale mutable source, so the guard
derives its evidence directly and keeps `MAIN.md` as the human-readable
declaration.

The dedicated workflow runs seven regressions and the live repository audit.
The regression set includes out-of-order parallel merges, stale and
future-declared MAIN states, missing evidence, and attempted advancement by
claim or unmerged-style implementation subjects.

## Problem-tree and claim status

The integrated continuation is rev244.  The forecast remains 576.  rev243
replaced one already-present primitive-Johnson leaf with a parent and two
explicit children, changing the effective count from 564 to 566; rev242 and
rev244 update already-counted leaves.  Since 566 is below 576, the mandatory
over-count rewrite is not triggered.  This operational guard consumes no AGI-GI
revision and does not overlap the live rev246 technical claim.

Root status remains **NOT_AGI**.  Repository-state consistency is necessary for
safe parallel integration but is not evidence of AGI generality, performance,
autonomy, or practical delivery.

## Whole-mechanism extension

The follow-up requirement extends recognition beyond the start marker.
`problem_solving_parallel_admission.py` binds forecast, leaf selection,
existing-solution audit, attempt, decomposition, evaluation, child/parent/root
integration, problem-tree update, publication, and merge to the same registry.
Read-only phases expose all occupied scopes; mutation phases require a fresh
schema-v2 owner, exact revision equality, descendant-only scope, and zero live
collision.  Parent integration therefore cannot silently absorb a child still
owned by another session.  The registry source SHA and digest make the visible
parallel state replayable as evidence.

The admission CLI can persist a complete phase record under
`agi/run-history/phase-admissions/`.  The PR workflow reconstructs the claim
registry from the record's exact source commit, reruns the phase decision, and
compares scope, revision, owner, parallel claims, conflicts, and digest.  A
problem-state diff without a changed replayable record is rejected, turning the
protocol from advisory text into an executable integration gate.

Cross-session interoperability is conservative.  A foreign record using a
singleton scope array or legacy base-SHA fields is retained as a blocking
claim, while `legacy=True` prevents it from authorizing an exclusive phase.
Ambiguous multi-scope records remain invalid.  This recognizes parallel work
without silently upgrading a malformed reservation into mutation authority.
