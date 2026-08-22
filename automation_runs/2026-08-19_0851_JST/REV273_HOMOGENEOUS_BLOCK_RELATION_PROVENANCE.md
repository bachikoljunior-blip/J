# Rev273 — homogeneous-block relation provenance certificate

## Scope

This revision closes one narrow upstream provenance subleaf left explicit by rev248.  Rev248 already gives an exact finite named unary/binary relation-structure isomorphism witness, but its audit deliberately does **not** prove the homogeneous-block reduction that feeds that relation image.

Rev273 adds a standalone verifier for the special case in which the caller already supplies source and target block partitions and a block bijection.  It certifies that the named unary/binary relations are genuinely constant on every relevant block fibre, that the quotient relation structures are therefore well-defined, that the supplied block bijection transports those quotient structures exactly, and that a canonical within-block lift transports the complete original explicit relations.

## Exact contract

`certify_homogeneous_block_transport` returns an exact certificate only after all of the following checks succeed:

1. both supplied partitions are nonempty-block, disjoint, exact covers of their domains;
2. source and target have identical named unary/binary relation signatures;
3. every unary relation is constant on each block;
4. every binary relation is constant on every ordered block pair, including diagonal block pairs;
5. the supplied block map is a bijection and maps only equal-size blocks;
6. the full quotient relation structure is transported by that block map; and
7. the deterministic sorted-within-block point lift is a bijection and independently transports every original named relation exactly.

Any malformed partition, nonuniform fibre, signature mismatch, block-size mismatch, nonbijective block map, quotient mismatch, or failed full-relation replay returns a fail-closed nonexact result with no certificate.

## Why this is useful

The certificate isolates a concrete condition under which a homogeneous block quotient is not merely a heuristic compression: the original explicit unary/binary relation structure factors through the block quotient, and an exact quotient transport has a mechanically replayed exact point-level lift.  This is a provenance bridge that can feed the already-integrated bounded-arity relation-image witness without assuming that an arbitrary proposed partition is equivariant or homogeneous.

## Verification

Focused local verification on the exact proposed implementation:

- 8 rev273 unit tests passed;
- `py_compile` passed for the rev273 module and tests;
- regressions cover a nontrivial relabelled exact transport, unary nonuniformity, binary block-pair nonuniformity, homogeneous quotient mismatch, block-size mismatch, malformed overlapping partitions, signature mismatch, and a nonbijective block map.

## Strict boundary

Rev273 does **not** discover or canonically choose block systems.  It does not prove that a caller's block system arises from the general CRX1 homogeneous-block theorem, handle relations that vary inside a block fibre, solve an implicit permutation-group image problem, establish a global quasipolynomial recurrence, or close CRX1, GI, or AGI.  AGI remains `NOT_AGI`.
