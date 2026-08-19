# rev100 — reuse solved global-search machinery across sibling leaves

Root remains **NOT_AGI**.

No duplicate implementation was created. The rev99 branch-and-bound engine already supplies the unresolved rev88 sibling `...c2d3b2b2c` (scalable witness search for duplicate-attribute combinatorial assignments): its 28-vs-30 regression uses seven repeated attribute buckets, two unmatched nodes and a positive edge-edit budget, and directly verifies a complete witness. Therefore that sibling is integrated as `solved_v0_1` by reuse.

Likewise the rev97 large-cycle fail-closed global-invariant path supplies the rev87 sibling `...c2d3b2b3` (hard symmetric/non-WL-distinguishable cases without fabricated identity): it finds a complete exact witness on an 80-cycle while certifying no identity because all invariant cells remain symmetric. Combined with rev96 bounded all-isomorphism intersection, this is sound ambiguity handling rather than arbitrary symmetry breaking. That sibling is integrated as `solved_v0_1`.

Thus the rev87 scalable alignment parent `...c2d3b2b` has all children solved at their stated bounded/typical semantics. The next unresolved sibling explicitly noted in rev87 is `...c2d3b2c`: noise-tolerant attribute handling.