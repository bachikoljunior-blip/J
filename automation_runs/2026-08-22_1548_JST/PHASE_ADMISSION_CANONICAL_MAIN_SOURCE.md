# Phase-admission canonical main source hardening

## Observed failure

`problem_solving_parallel_admission.py` previously persisted the current
`HEAD` as `registry_source_sha`.  A rebased, amended, synthetic-merge, or
cherry-picked local commit can be a sibling of the eventual published main
commit.  Such evidence passes local payload validation but correctly fails the
repository-wide replay guard because its source is not an ancestor of the
proposed head.

## Reused mechanism

The existing evidence guard already uses Git's ancestry relation and replays
the registry at the recorded commit.  Generation now reuses the same invariant:
it resolves canonical `origin/main` and records `merge-base(HEAD, origin/main)`.
If the main ref is missing or there is no provable common ancestor, generation
fails closed before writing evidence.  `--main-ref` permits an explicit
canonical ref in controlled test or CI environments.

## Verification boundary

Regression tests prove that a synthetic child commit is not recorded when its
real main ancestor is available, and that a missing canonical main ref is
rejected.  This change hardens coordination evidence only.  It does not solve
String Isomorphism, Graph Isomorphism, or establish AGI.
