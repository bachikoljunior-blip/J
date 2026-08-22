# Phase-evidence workflow self-protection

## Observation

The parallel-admission workflow already triggers when its own YAML changes, but
`is_problem_state_path` did not classify that file as protected problem state.
A workflow-only commit could therefore alter or disable enforcement without a
changed phase-admission evidence record.

## Resolution

The workflow path is now a named protected constant in the shared classifier.
Consequently, pull requests and direct `main` pushes that change the enforcement
workflow must carry replayable evidence covering that exact path. Existing
commit-local push checking and current-registry re-admission remain the single
verification path.

## Existing-solution audit

This reuses the established self-protecting-CI pattern and the repository's
existing path classifier. No second verifier or parallel policy language is
introduced.

## Scope and status

This closes a repository-coordination fail-open leaf. It does not expand the
solved String-Isomorphism instance class and does not establish AGI. State:
`NOT_AGI`.
