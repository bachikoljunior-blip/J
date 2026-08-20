# AGI-GI rev218 execution-linked accounting proof

## Selected leaf and direct attempt

The selected leaf was CRX3 child 4: a replay-stable proof/resource identity spanning
the rev207 polynomial auxiliary lift and nested S1.  Direct code-path inspection
found a concrete accounting defect boundary before attempting a generic DAG:
`solve_design_witness_cover_in_parent_bipartite_action` already executes candidate
String Isomorphism once per rev206 branch, but rev207's
`_trace_exact_image_proof` executed the same solver again solely to recover its
accounting tree.  Only one child proof charge was then composed.  Determinism of
the replay does not make the second execution free.

rev218 removes that replay.  `BipartiteParentActionCosetIntersection` now captures
the exact immutable `ProofCarryingCoset` returned by the actual auxiliary-image SI
execution, for exact, exact-empty, unresolved, and failed-preimage continuations
after the SI call.  The polynomial-lift certificate consumes that same object by
identity.  If it is absent, nonexact, or status-inconsistent, accounting fails
closed; it never reconstructs a replacement proof.

## Problem-tree decomposition

The direct attempt proves that the former single CRX3 child 4 needs three children
whose integration is sufficient for the parent:

1. **execution-linked rev206/rev207 proof capture** — solved here; remove duplicate
   solver work and require the execution object for polynomial-lift accounting;
2. **nested S1 mathematical identity** — unresolved; freeze group/coset orientation,
   source/target strings, root/measure, dispatcher and every resource gate for each
   recursively shared S1/candidate proof node;
3. **shared proof-DAG cost verifier** — unresolved; check acyclicity and identity
   collisions, distinguish proof reuse from executed work, preserve conservative
   worst-case charges on cache hits, and lift the composed bound to the original
   root.

Replacing one unresolved leaf with three children changes the effective count from
517 to `517 - 1 + 3 = 519`; the forecast remains 576.  The mandatory over-count
rewrite does not fire because 519 is below 576.  No child was suppressed to avoid
the trigger.

## Existing-world containment audit

The cross-layer shape follows content-addressed DAG/hash-consing and incremental
build systems, where complete action/input identity controls reuse, plus standard
amortized/potential accounting, where sharing storage does not erase executed
cost.  Bazel's remote-cache documentation is a concrete existing example of
action-key/result separation: <https://bazel.build/remote/caching>.  J does not
treat a cache hit or object identity as a mathematical proof.  Exact SI evidence,
orientation, recurrence progress, resource gates, and worst-case work remain
separate mechanically checked obligations.

The next selected leaf is child 2, nested S1 mathematical identity.  Child 3 must
then integrate the captured rev207 object and nested S1 identities into one
independent cost verifier.

## Claim boundary

This revision removes one real double-execution/accounting mismatch.  It does not
yet provide the shared global proof DAG, complete corrected Split-or-Johnson,
W1R-H6 closure, global quasipolynomial recurrence, or practical AGI.  State:
`NOT_AGI`.

