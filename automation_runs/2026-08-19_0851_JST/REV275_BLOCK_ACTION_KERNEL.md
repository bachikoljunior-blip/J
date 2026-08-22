# AGI-GI rev275 — homogeneous block-action kernel factorization

## Scope

Durable takeover claim: `chatgpt-session-j-rev275-kernel-takeover-20260822T114426JST-eda21ac0`.

Exclusive scope: `crx3/block-structured-consumers/homogeneous-block-action-kernel-factorization`.

This revision closes one narrow consumer boundary above the main-integrated rev274 block-action provenance certificate.  Given a replay-valid rev274 certificate, it independently reconstructs the source and target permutation groups, their induced quotient actions, and the kernels of those actions.  It then certifies the first-isomorphism factorization on both sides.

## Existing-world containment audit

The required group machinery already exists in the world and in the reachable rev series: Schreier--Sims stabilizer chains, action kernels, and the first isomorphism theorem.  Rev275 therefore does not invent a new group algorithm.  It composes and independently replays the main-integrated `permutation_group_schreier.py` and `block_action_preimage_coset_v1.py` implementations, while treating the rev274 provenance certificate as an untrusted supplied premise until replay succeeds.

## Exact contract

`certify_block_action_kernel_factorization`:

1. replay-verifies the supplied rev274 block-action provenance certificate;
2. builds exact stabilizer-chain certificates for both original groups and both quotient images;
3. reconstructs paired quotient preimages and their residual kernel generators;
4. independently certifies both residual kernel orders;
5. requires `|G| = |ker(action)| * |image(action)|` for source and target;
6. freezes every order, generator family, resource bound, and premise digest into a deterministic SHA-256 transcript; and
7. accepts replay only when recomputation reproduces the complete frozen result.

Malformed provenance, mismatched paired generators, an invalid group/action certificate, factorization failure, transcript tampering, or any resource-bound failure returns a non-exact result.

## Resource fail-closed correction

The inherited attempt counted only the supplied generator/action-point input scan.  That count did not bound the subsequent Schreier orbit, Schreier-generator, paired-chain, and residual-kernel constructions.  Rev275 now computes a conservative saturated upper bound for every chain on both source and target sides before starting any Schreier construction.  Arithmetic saturates at `cap + 1`; a non-integer cap or a bound above the cap fails closed before group materialization.  The result records the admitted work bound and replay uses the same cap.

## Strict boundary

This revision does **not** discover a block system, prove relation homogeneity, construct a quotient relation, solve quotient string isomorphism, lift quotient solutions, prove original-root quasipolynomial accounting, or integrate a production parent.  It certifies only kernel/image factorization for the supplied, replay-valid rev274 paired block actions.

Consequently it does not close CRX3, Graph Isomorphism, or AGI.  The empirical state remains `NOT_AGI`.

## Problem-tree accounting

The forecast remains 576 parent/child problems and the current effective count remains 571.  The effective count does not exceed the forecast, so the over-count rewrite procedure is not triggered by this revision.

## Focused validation

- focused rev275 regressions: 12/12 success;
- implementation and test syntax compilation: success;
- tight resource-cap rejection occurs before any Schreier-chain call;
- transcript tampering, premise tampering, wrong replay input, invalid caps, and the trivial-group boundary fail or certify exactly as specified.
