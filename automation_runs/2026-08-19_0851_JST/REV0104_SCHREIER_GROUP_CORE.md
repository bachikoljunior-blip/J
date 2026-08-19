# rev104 — Schreier stabilizer-chain group core

Root remains **NOT_AGI**.

The permutation-group primitive leaf was attempted by implementing a deterministic Schreier stabilizer chain for permutation groups represented by generators.

The implementation defines explicit permutation composition/inversion conventions, computes point orbits with transversal permutations, derives successive stabilizer generators using Schreier's lemma, and builds a full base chain. The product of orbit sizes gives the represented group order. Membership is decided by sifting a candidate permutation through the stored transversals. Arbitrary point orbits under the original generating set are also exposed.

In-session validation compared the implementation with independent exhaustive group closure on **400 random generated groups of degree 1 through 6**, with 1–3 random generators. For every case the stabilizer-chain order equaled the exhaustive group size; sampled arbitrary permutations had identical membership decisions; and every point orbit matched the orbit computed from all explicitly enumerated group elements. Focused S3 and cyclic-subgroup tests were also added.

The broad permutation-group child `...c3c3c2` is not yet solved because Luks/Babai-style recursion needs more than group membership and point stabilizers. It is decomposed into:

- `...c3c3c2a`: Schreier stabilizer chain, membership, order, and point orbits — `solved_v0_1`;
- `...c3c3c2b`: explicit coset arithmetic plus arbitrary point/pointwise stabilizer generators and validated coset membership — unresolved;
- `...c3c3c2c`: set/string stabilizers, transporter/coset-intersection operations, and divide-and-conquer restrictions required by the higher-level isomorphism recursion — unresolved.

Estimated active-node count after decomposition: **491**, below prediction **512**.
