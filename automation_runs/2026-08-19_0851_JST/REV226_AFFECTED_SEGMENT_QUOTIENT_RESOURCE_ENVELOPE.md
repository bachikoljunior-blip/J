# AGI-GI rev226: affected-segment quotient/kernel resource envelope

## Status

This revision candidate solves only CRX2 child 2.2.2.2b. It preflights the
quotient point-image recursion through singleton lifts and kernel-orbit child SI.
Parent coset reassembly, the complete layer sum, all-T multiplicity, and the AGI
root remain unresolved. State remains `NOT_AGI`.

## Existing-world inclusion audit

The implementation follows the Luks orbit/block/coset divide-and-conquer shape,
Babai's affected-kernel-orbit reduction, and reusable Schreier homomorphism
mechanisms provided by systems such as GAP. Existing implementations are not
treated as a complexity proof: the envelope enumerates the exact primitive
families executed by J and charges them before starting the recursion.

## Bound and execution changes

The exact quotient image order is an upper bound on singleton leaves. A depth at
most `t` gives `1 + t * leaves` quotient nodes. Each leaf has at most `n` active
kernel-orbit children, and every child may observe `max_child_nodes + 1` point-
image nodes including the fail-closed rejecting tick.

The saturating work sum covers:

- quotient orbit transversals, point stabilizers, and subgroup chains;
- one shared block-action image/paired-kernel preparation;
- every singleton quotient sift/lift;
- kernel-orbit discovery and orbit image chains;
- recursive child intersection nodes, Young subgroup construction, membership
  sifts, and subgroup reconstruction;
- every paired orbit-action kernel, lift, and preimage subgroup chain.

If the exact quotient order exceeds the leaf cap, or the work sum exceeds the
finite cap, the executor returns unknown before preparing the quotient
homomorphism or entering the recursion. If admitted, one frozen preparation is
reused by all singleton leaves instead of rebuilding the same paired chain and
kernel once per leaf.

The already executed rev225 giant-action certificate is passed into the segment
executor, preventing an additional structural audit from being mistaken for
quotient work.

## Evidence and remaining boundary

Regression tests cover fail-before-preparation for both leaf and work caps,
cap-plus-one saturation, all multiplicity formulas, one-preparation reuse across
120 exact `S_5` quotient leaves, and equality with the previous exact bounded
result. The next child must bound exact parent coset reassembly and connect its
actual child charges to the complete single-T execution sum.
