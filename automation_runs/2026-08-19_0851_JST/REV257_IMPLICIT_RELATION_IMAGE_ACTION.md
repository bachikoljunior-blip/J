# AGI-GI rev257: implicit relation-image paired action

## Solved child

For named unary/binary relations and a permutation group supplied by generators,
construct the faithful point/incidence auxiliary action without enumerating the
group.  A paired Schreier chain certifies its exact image, kernel, and order
identity.  The neutral point layer makes the kernel trivial.

All auxiliary-degree, generator-count, and generator/action-point work caps are
checked before the first induced auxiliary generator is materialized.  Cap
failure is fail-closed.

## Reused existing mechanisms

- rev256's canonical unary/binary feature string and induced incidence action;
- `permutation_group_schreier` for implicit domain/image groups;
- the paired Schreier chain used by exact quotient/preimage reconstruction.

## Strict boundary

This solves only rev257 child (1).  It does not yet intersect the implicit image
group with the complete value-preserving right coset, lift that result back to
the original domain, or prove a quasipolynomial original-root work envelope.
Those remain children (2) and (3).  GI and AGI remain unproved (`NOT_AGI`).
