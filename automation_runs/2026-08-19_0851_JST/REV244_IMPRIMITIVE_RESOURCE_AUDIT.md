# rev244 transitive-imprimitive quotient/kernel resource audit

## Scope

This revision advances the already-counted nested transitive-imprimitive resource
leaf.  It does not claim corrected Split-or-Johnson closure, global
quasipolynomial closure, or AGI.  Root status remains **NOT_AGI**.

The parallel-execution marker for this session was rescoping-aware: the shared pipeline-ledger leaf was already claimed by PR #170, and the
primitive-Johnson sibling later took rev243 in PR #174.  This implementation
therefore uses rev244 and modifies neither parallel branch.

## Executable boundary

The existing unique canonical block-system recursion had exact mathematics but
no one-shot finite admission spanning all of these phases:

1. block-action image construction and paired Schreier preparation;
2. complete quotient-image enumeration;
3. every full-domain quotient lift;
4. every kernel-fiber String-Isomorphism child; and
5. final disjoint-fiber right-coset reconstruction.

`imprimitive_quotient_kernel_resource_v1.py` supplies one caller-cap-saturating
envelope before the first block action.  It uses only exact input-derived bounds:

- quotient image order at most `min(|G|, q!)`;
- because the point action and induced action on `q` invariant blocks are
  transitive, quotient kernel order at most `|G|/q`;
- the existing exact small-order terminal below its gate;
- otherwise the complete string-state orbit bounded by both the kernel order and
  the target multiset image count; and
- raw Schreier-chain bounds already used by the repository's other resource
  proofs, including the full paired-group order rather than only the quotient
  order; and
- final reassembly membership sifts charged against the ambient group order.

All saturation is at the caller's arbitrary-precision `cap+1`.  Rejection occurs
before the first prepared block homomorphism.  Admission is execution-linked:
the prepared homomorphism must be built exactly once, the exact quotient order
and fiber count must fit their reservations, every child must be exact, and
observed permutation scans must stay within the terminal bound.

## Reuse and cross-cut

`resource_bounded_imprimitive_candidate_si_v1.py` reuses the repository's
canonical block certificate snapshot, prepared paired block-action preimage, exact
small-order candidate terminal, exact state-orbit terminal, and cardinality
audited coset reconstruction.  The prepared homomorphism is shared across all
quotient lifts instead of being rebuilt for each fiber.  Its accounting keeps
the existing `imprimitive_small_quotient` operation kind, so recurrence-v4 accepts
exact terminal fibers without introducing an unrecognized progress category.

`u2_candidate_coset_string_iso_v8.py` is a drop-in, opt-in candidate dispatcher.
With a zero resource budget it delegates unchanged to v7.  With a positive
budget, only the unique transitive-imprimitive status is intercepted; a rejected
envelope remains fail closed and an exact subgroup result is translated back to
the original right-coset coordinates.

## Remaining boundary

The new v8 dispatcher is intentionally not substituted globally during this
parallel run.  The next nonconflicting integration step is to thread its explicit
budget through the shared S1/Design caller ledger after the independently active
rev242 pipeline work settles.  Primitive non-giant Johnson/profile resource
preflight remains a separate sibling.
