# rev103 — worst-case scalable canonical-labeling direct attempt and decomposition

Root remains **NOT_AGI**.

The remaining leaf demanded worst-case scalable exact canonical labeling / automorphism handling for general cyclic and highly connected graphs. Existing rev97–rev102 paths do not satisfy that requirement: they cover structural polynomial families, shallow/refinement-discrete cases, or explicitly resource-bounded backtracking. Treating those as a general scalable solution would lower the criterion, so this leaf remains unresolved.

Primary-source algorithmic guidance was checked before decomposing the problem. Babai's graph-isomorphism algorithm establishes a quasipolynomial worst-case bound for general GI and related string-isomorphism/coset-intersection problems (arXiv:1512.03547). The later exposition by Helfgott, Bajpai, and Dona (arXiv:1710.04574) emphasizes the isomorphism-coset viewpoint and the Luks permutation-group framework, including the bounded-degree case. This makes a permutation-group core and canonical partition/local-certificate machinery necessary implementation layers rather than optional performance tweaks.

The leaf is decomposed into:

- `...c3c3c1`: freeze the exact algorithmic contract: return an isomorphism coset / automorphism generators or a certified non-isomorphism result, with canonical labeling derived without arbitrary vertex choices and a worst-case quasipolynomial ceiling for the fully general path — `solved_v0_1` at specification level;
- `...c3c3c2`: implement and validate permutation-group primitives needed by Luks/Babai-style recursion (stabilizer chains, membership, orbits, set/string stabilizers, coset operations) — unresolved;
- `...c3c3c3`: implement canonical partitioning / local-certificate recursion and compose it with the group core into exact general graph isomorphism/canonical labeling — unresolved;
- `...c3c3c4`: adversarial correctness and scaling validation against independent oracles and hard symmetric graph families — unresolved.

Estimated active-node count after decomposition: **488**, below prediction **512**.

No claim is made that the current repository implements Babai's general algorithm; this revision only freezes the non-weakened target and converts the monolithic leaf into implementable mathematical layers.
