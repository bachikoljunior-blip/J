# rev98 — scalable twin/module quotient orbit certificate

Root remains **NOT_AGI**.

Resolved scalable symmetry child `...c2d3b2b2b3c3b` at `solved_v0_1` for verified true/false-twin modules.

The implementation detects equal-attribute vertex groups whose adjacency to every outside vertex is identical and whose internal adjacency relation is uniform. Such a verified group is an exact module: arbitrary permutations inside a non-singleton group are graph automorphisms. The original graph is compressed to a quotient whose vertices carry `(attribute, module size, internal clique/independent relation)` metadata and whose edges are the uniform inter-module adjacencies.

Exact quotient isomorphisms are then enumerated on the compressed graph. An original identity pair can be forced only when its quotient-module correspondence is forced and both the source and target modules are singletons. Any pair involving a non-singleton module is movable by an explicit within-module automorphism and therefore cannot be an individually forced identity. If the currently verified quotient-witness intersection contains no singleton-module original pair, the implementation can already certify no original forced identities; otherwise nonempty identities are released only after complete bounded quotient enumeration.

Validation mirrored in-session:

- Uniform clique: all vertices compress to one verified twin module; no identity is forced.
- Large star: quotient has two modules (singleton center and all leaves); only the center correspondence is forced while all leaves remain exchangeable.
- `K_5,5` with identical attributes: the two false-twin modules admit within-module permutations and no original identity is forced.

Repository tests include a 300-node clique and a 401-node star to exercise the compression path at sizes where enumerating original graph automorphisms would be unnecessary.

The remaining scalable-symmetry child is `...c2d3b2b2b3c3c`: general scalable automorphism/orbit handling beyond the recognized cycle and twin/module families.

Active problem count remains **478**, below prediction **512**.
