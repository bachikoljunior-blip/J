# REV253 — complete ordered two-root UPCC split family

## Existing-solution audit

Babai's quasipolynomial GI/SI framework makes canonical colorings and Johnson structure the two progress mechanisms at the primitive barrier, while Helfgott–Bajpai–Dona's detailed account emphasizes functorial canonicity and records that the repaired proof changed the problematic Split-or-Johnson recursion. Primary sources: [Babai, *Graph Isomorphism in Quasipolynomial Time*](https://arxiv.org/abs/1512.03547) and [Helfgott–Bajpai–Dona, *Graph isomorphisms in quasi-polynomial time*](https://arxiv.org/abs/1710.04574).

The implementation-level inference is deliberately narrower than the theorem: the set of every ordered injective pair is equivariant under relabeling, so exhaustive two-constant k-WL can certify a canonical split family when every branch splits. It does **not** follow that two roots replace the corrected general Split-or-Johnson routine. Any pair branch that stays UPCC or exposes an unimplemented Johnson alternative remains unresolved.

## Contract

`certify_upcc_pair_root_split_family` first reserves the base full-ground UPCC check and all `v(v-1)` ordered pair runs. It rejects before the first k-WL execution when the branch count, one-run tuple state space, or complete worst-case work sum exceeds the caller's finite cap.

After admission it:

- mechanically confirms the unmarked exact outcome is a full-ground homogeneous UPCC;
- reruns exact correlated-replacement k-WL for every injective ordered pair `(a,b)`, preserving mark order;
- accepts a branch only when the marked result is an alpha-bounded canonical point coloring or alpha-bounded imprimitive partition;
- records every branch status, partition, actual work charge, complete-cover reservation, and `2 log2(root_n)` multiplicity bound;
- reports exact but unresolved when the complete cover contains any other structural outcome.

The Petersen UPCC regression is substantive: its one-root subconstituent sizes include a cell of size six at `alpha=1/2`, while all 90 ordered two-root runs yield canonical cells of size at most four.

## Parallel boundary

The durable claim is `chatgpt-session-j-rev253-takeover-20260822T041903JST-b5a5588c`. All changes are new rev253-specific paths, and the active rev255 shared Design caller files are untouched.

This resolves only the bounded complete ordered-pair alpha-split terminal. Source/target pair matching, ambient/full-string SI, surviving UPCC/Johnson branches, corrected general Split-or-Johnson, W1R-H6, and the AGI root remain unresolved. AGI state remains `NOT_AGI`.
