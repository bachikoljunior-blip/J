# rev95 — exact intrinsic-symmetry/orbit certificate

Root remains **NOT_AGI**.

The intrinsic-symmetry leaf is decomposed rather than treated as one monolithic search problem.

For the exact/full subcase, rev95 adds bounded attributed-isomorphism enumeration with a crucial fail-closed intersection rule. Every enumerated mapping satisfies equal attributes and exact adjacency consistency. The intersection of a subset of valid mappings is always a superset of the true all-mapping forced-pair intersection. Consequently, if the intersection of already verified mappings becomes empty, `no forced pairs` is proven immediately even if enumeration has not completed. Conversely, nonempty forced pairs are released only after complete enumeration; hitting a state or witness limit with a nonempty intersection returns no identities.

This directly captures automorphism/orbit ambiguity without arbitrary symmetry breaking. Symmetric cycles can therefore be certified as having no forced identity, while asymmetric graphs can have their exact unique mapping certified after complete bounded enumeration.

The intrinsic-symmetry parent is decomposed into:

- `...c2d3b2b2b3c1`: bounded exact/full orbit certificate by verified-isomorphism intersection — `solved_v0_1`;
- `...c2d3b2b2b3c2`: bounded partial-edit alternate-witness/orbit certificate — unresolved;
- `...c2d3b2b2b3c3`: scalable symmetry/orbit reasoning beyond bounded backtracking — unresolved.

Estimated active-node count after decomposition: **475**, below prediction **512**.
