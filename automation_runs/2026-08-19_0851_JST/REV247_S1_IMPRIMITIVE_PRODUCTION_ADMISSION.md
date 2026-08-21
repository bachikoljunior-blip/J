# rev247 shared-S1 transitive-imprimitive production admission

## Scope

This revision closes only the shared-S1 caller boundary left explicitly separate by
rev244 and rev245.  It does not modify the Design caller owned by rev245/rev255,
primitive-Johnson production work, canonical imprimitive-family handling, or any
other active parallel scope.  AGI state remains **NOT_AGI**.

## Existing solution reused

rev244 already provides the exact reserve-before-execute machinery:

- `resource_bounded_imprimitive_string_isomorphism` reserves the complete unique
  canonical block-system quotient/kernel phase before block-action preparation;
- every quotient lift is forced through an exact small-order or complete
  state-orbit child under that reservation;
- execution is checked against the reservation and the exact quotient fibers are
  cardinality-audited back into one right coset; and
- candidate dispatcher v8 is a drop-in wrapper around v7: with budget zero it
  delegates unchanged, while a positive budget intercepts only the unique
  transitive-imprimitive status and preserves fixed right-coset coordinates.

The missing boundary was that the shared `s1_string_isomorphism_v4` dispatcher
still called candidate v7 directly, so an S1 caller had no explicit way to opt
into rev244's complete finite admission contract.

## Change

`S1 v4` now accepts the explicit nonnegative caller cap
`max_imprimitive_quotient_kernel_work`, defaulting to zero.

- Zero preserves the historical path because S1 enters candidate v8 and v8
  delegates exactly to v7 before any new classification or resource execution.
- A positive value is threaded through every nested S1 orbit child.
- For a unique canonical transitive-imprimitive block system, candidate v8 uses
  the already-certified classification snapshot and runs rev244's resource-bounded
  quotient/kernel operator.
- Canonical imprimitive families continue through v7 unchanged; no block system
  is chosen from an equally canonical family.
- A rejected resource envelope remains unresolved and no block-action preparation
  starts.

The existing quotient-cap widening for a mathematically small quotient is kept
unchanged and is passed into v8 as the quotient/candidate group gate.  The new
work cap is independent and only controls the complete rev244 phase reservation.

## Replay identity

The S1 proof identity now records both the v8 dispatcher identity and the exact
`max_imprimitive_quotient_kernel_work` value.  Thus a proof obtained with legacy
zero-budget delegation cannot be replayed as though it came from a positive
reserve-before-execute run, and two different caller caps are distinct immutable
execution identities.

## Regression contract

The rev247 regression covers five boundaries:

1. default zero budget reaches v8's exact v7 delegate;
2. a positive budget reaches the real rev244 unique-imprimitive operator and
   produces a complete resource envelope;
3. an insufficient budget fails closed before prepared block-action construction;
4. the imprimitive work cap is part of S1 replay identity; and
5. negative budgets are rejected rather than silently interpreted as legacy mode.

The dedicated workflow also reruns rev244 and nested-S1 identity regressions to
ensure the integration does not weaken the underlying resource proof or existing
execution-identity guarantees.

## Remaining boundary

This admission is only for the unique canonical transitive-imprimitive shared-S1
path.  Family-aware imprimitive cases remain on their established v7 machinery,
and primitive non-giant Johnson/profile production admission is a separate leaf.
Nothing here establishes the full corrected Split-or-Johnson theorem, global
quasipolynomial closure, graph isomorphism closure, or AGI.
