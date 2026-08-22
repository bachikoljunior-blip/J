# AGI-GI rev278 — homogeneous block quotient preimage lift

## Scope

rev274 certifies that supplied homogeneous source/target block systems carry paired, exactly intertwined quotient actions. The repository already has a generic paired-Schreier primitive that computes the exact preimage of one quotient permutation under a block action. rev278 binds those two facts together without widening either theorem boundary.

`lift_certified_block_quotient_preimage` first replays the immutable rev274 provenance. For the selected `source` or `target` side it reconstructs exactly the certified generator group, prepares the induced block-action homomorphism, checks `|G| = |ker| |im|`, and sifts one caller-supplied quotient permutation through the paired Schreier chain.

A successful sift returns a replayable certificate for the complete original-domain right coset `ker(phi) * r`. A failed exact sift returns exact empty, because the requested quotient permutation is proved outside `im(phi)`. Invalid provenance, malformed quotient input, or any inconsistent generic evidence fails closed.

## Deliberate non-goals

This revision does not discover block systems, construct or solve quotient String-Isomorphism, infer generator pairing, prove relation homogeneity, duplicate rev275 kernel-factorization work, consume rev273 branch-only relation provenance, perform parent orchestration, or claim an AGI result. It lifts exactly one already-specified quotient permutation through an already-certified block action.

The main new invariant is provenance binding: every accepted nonempty or exact-empty result includes the exact rev274 certificate digest and is reproducible by replaying rev274 before repeating the paired Schreier sift.

## Regression witness

The focused regression uses eight domain points in four 2-point blocks. A global within-block involution and a 4-cycle of blocks generate a group of order 8 whose quotient image has order 4 and kernel order 2. The test checks a nontrivial source lift, the target-side lift, exact emptiness for a quotient transposition outside the cyclic image, rejection of tampered rev274 evidence, fail-closed malformed inputs, and replay rejection after result tampering.

AGI state: `NOT_AGI`.
