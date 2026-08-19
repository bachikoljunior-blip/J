# rev111 — exact end-to-end GI isomorphism coset integration

Root remains **NOT_AGI**.

The remaining canonical-partitioning/labeling integration leaf was too broad to mark solved by a single exact primitive. It is decomposed into three children without weakening the original target:

1. produce an exact end-to-end graph-isomorphism **coset certificate** and exact automorphism generators without enumerating every automorphism;
2. derive an isomorphism-invariant canonical labeling using exact automorphism-stabilizer orbit pruning;
3. establish the missing worst-case scalable/quasipolynomial general-path machinery and adversarial scaling evidence.

This revision solves child 1.

`exact_gi_isomorphism_coset.py` first finds one directly verified A→B witness by exact individualization/refinement search. It then reconstructs `Aut(B)` by orbit-stabilizer recursion: for a canonically selected non-singleton refined class, the point stabilizer is solved recursively and every claimed orbit image is admitted only after a directly verified automorphism transporter is found. The resulting group is checked against `|G| = |G_u| * |Orb_G(u)|`. The complete isomorphism set is returned as the exact right coset `p * Aut(B)`.

Independent local execution validation:

- 160 deterministic random attributed graph pairs of degree/order n=1..7 were checked against brute-force enumeration of **every** vertex permutation. Non-isomorphism decisions, isomorphism counts, and right-coset membership all matched exactly. Maximum search nodes observed: 22.
- Complete graphs K5, K7, K9 reconstructed automorphism orders 120, 5,040, 362,880.
- Empty and complete graphs at n=10 reconstructed order 3,628,800 in 350 search nodes; at n=12 reconstructed order 479,001,600 in 596 nodes, without enumerating those automorphisms.
- Cycles C5, C8, C12 reconstructed exact dihedral automorphism orders 10, 16, 24.

This is exact end-to-end GI/coset evidence, not a worst-case quasipolynomial guarantee. Children 2 and 3 remain open.