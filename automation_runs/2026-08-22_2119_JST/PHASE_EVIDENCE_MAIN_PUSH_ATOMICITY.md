# Main-push phase-evidence atomicity

## Selected leaf

The phase-admission workflow previously ran only for pull requests. Direct
main writes could therefore publish a problem-state change in one commit and
its phase evidence in another, even though the guard itself correctly rejects
that commit-local shape when given the exact changed-file set.

## Existing-solution audit and implementation

GitHub Actions push path filters and Git's first-parent commit diff already
provide the needed boundary. The existing workflow now also runs for pushes
to `main`. Pull requests retain the merge-base diff and `origin/main` current
registry. A main push instead diffs exactly `HEAD^..HEAD` and uses `HEAD^` as
the current pre-write registry. The same evidence guard performs immutable
source replay, registry ancestry continuity, and current-registry
re-admission; no parallel verifier is introduced.

This is a repository coordination guarantee, not an AGI capability. It does
not expand the solved String-Isomorphism class or prove GI. Forecast: 576
problems; effective: 571; overflow rewrite not triggered. State: `NOT_AGI`.
