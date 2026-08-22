# rev276 — joint homogeneous block-reduction compatibility

## Scope

This revision certifies one narrow composition boundary between two independently owned proof artifacts:

- rev273 / PR #219 supplies an **already exact** homogeneous unary/binary relation block-transport result;
- integrated rev274 supplies an **already exact and replayable** group block-action equivariance certificate.

rev276 proves only that those artifacts refer to the identical canonical source partition, target partition, block bijection, domain degree, block count, and uniform block size. It also verifies that the rev273 point lift realizes that same block bijection and independently recomputes the rev274 certificate digest before emitting a joint SHA-256 identity.

## Fail-closed rules

No joint exact certificate is emitted when any of the following occurs:

- rev273-style relation evidence is not explicitly exact or has no certificate;
- source or target partitions differ after canonicalization;
- the raw relation block map canonicalizes to a different block bijection;
- the relation point lift crosses the common block map;
- quotient block counts/sizes or relation signatures are inconsistent;
- the rev274 action certificate is not exact/complete, has malformed dimensions, nonpaired generators, nonintertwining quotient generators, or a bad digest;
- any input needed for the frozen joint identity is malformed.

## Parallel boundary

This module does not import the branch-only rev273 implementation and does not modify any rev273 path. It does not rediscover block systems, re-prove relation homogeneity, construct quotient relations, infer generator pairings, solve an image/preimage problem, or perform resource accounting. It writes only rev276-reserved additive paths.

rev275 is deliberately left unclaimed for the separately started continuation observed at 2026-08-22T09:42:35+09:00. All sibling claims, branches, PRs, workflows, `MAIN.md`, and shared implementations remain untouched.

## Result boundary

A successful rev276 result means only: **the exact upstream relation artifact and exact upstream action artifact are compatible descriptions of one supplied block reduction**. It is not by itself a String-Isomorphism solution and does not close CRX1, GI, or AGI.

AGI state remains `NOT_AGI`.
