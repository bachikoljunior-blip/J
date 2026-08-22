# Current-registry ancestry continuity

## Selected leaf

The current-registry re-admission added by PR #291 resolves an explicit ref and
checks the live claim set, but it must also establish that this registry is a
continuation of the immutable `registry_source_sha`. Without that relation, a
caller could select a disjoint commit whose claims happen to admit the phase.

## Existing-solution audit and implementation

The repository already uses `git merge-base --is-ancestor` to bind persisted
evidence to the proposed head. This child reuses the same primitive to require
the persisted source to be an ancestor of the resolved current-registry commit
before loading or re-admitting its claims. A synthetic parentless commit with
an otherwise admissible registry verifies the fail-closed boundary.

This changes coordination evidence only. It does not expand the solved
String-Isomorphism class, solve GI, or demonstrate AGI. The forecast remains
576 problems with 571 effective problems, so the overflow rewrite is not
triggered. State: `NOT_AGI`.
