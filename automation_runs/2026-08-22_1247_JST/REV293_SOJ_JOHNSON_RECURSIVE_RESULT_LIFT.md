# Rev293 — exact recursive Johnson-ground result lift

## Boundary

Rev293 closes only the **post-recursion transport** edge for the larger-ground
Johnson route. It starts after a caller has already replayed a certified
complete `J(v,k) -> v` relational reduction and after a recursive solver has
returned an exact, complete, canonical result on that certified ground action.
It does not construct the Johnson reduction, run recursive String Isomorphism,
or perform recurrence/cost accounting.

The implementation is deliberately file-disjoint from the active rev287,
rev291, and rev292 branches. Their branch-only Python modules are not imported.
Instead rev293 consumes the published rev287 evidence shape structurally and
requires the caller to assert, with a strict boolean, that the upstream
reduction was independently replayed first.

## Exact nonempty route

For a child ground coset, rev293 requires exact, complete, canonical child
evidence; a deterministic SHA-256 child snapshot identity; the exact certified
Johnson-ground degree and reduction identity; separately certified membership
in the induced ground action; and a canonical ground representative plus
canonical target-stabilizer generator list.

Every supplied ground permutation is induced mechanically on **all** `k`-subset
vertices. The lifted representative is then checked on the original parent
source/target strings and every lifted stabilizer generator is checked against
the original target string. Only after those checks does rev293 emit an exact,
complete parent coset-lift certificate.

## Exact-empty route

An exact-empty child result carries no representative or stabilizer generators.
Because the upstream reduction must independently certify exact solution
transport, exact child emptiness implies exact parent emptiness. Rev293 records
that implication with a deterministic transcript; it does not fabricate a
coset.

## Fail-closed and replay policy

The adapter rejects malformed Johnson dimensions, incomplete or duplicated
`k`-subset coordinates, unreplayed reductions, reduction/child identity drift,
coercible booleans, malformed permutations, noncanonical generator ordering,
tampered child identities, non-JSON/opaque parent values, non-finite values,
failed parent transport, failed target stabilization, and replay drift.

This remains a local corrected Split-or-Johnson transport certificate. The
construction/cost-binding work owned by rev287/rev292, the recursive handoff
owned by rev291/rev292, production caller wiring, complete recurrence closure,
GI, and AGI remain separate obligations. AGI state is `NOT_AGI`.
