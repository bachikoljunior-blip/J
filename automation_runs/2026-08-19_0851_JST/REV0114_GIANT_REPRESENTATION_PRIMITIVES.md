# rev114 — giant-representation and affected/unaffected primitives

Root remains **NOT_AGI**.

The rev113 remaining worst-case leaf was directly checked against Babai's primary algorithm description (arXiv:1512.03547). A complete general implementation cannot honestly be claimed from the existing resource-bounded IR path. The leaf is therefore decomposed into four necessary layers:

1. giant quotient / kernel / affected-unaffected group primitives;
2. local fullness/non-fullness certificates on logarithmic test sets;
3. certificate aggregation plus canonical partition / Split-or-Johnson reduction;
4. master recursion with a verified quasipolynomial multiplicative-cost bound and canonical-label integration.

Estimated active-node count after this decomposition: **503**, still below the frozen prediction **512**.

This revision solves layer 1 at the supplied invariant-block-action level.

`giant_block_action_certificates.py` derives the induced homomorphism `phi:G->S_k` from generator action on a designated invariant family of blocks. Crucially, it computes `ker(phi)` by **paired Schreier recursion**: the algorithm runs Schreier stabilizer recursion only on the k-point quotient while carrying matching preimage words, so it does not enumerate S_k or the full source group. It then:

- certifies exact image, kernel, and source-group orders with `|G|=|ker(phi)|*|im(phi)|`;
- recognizes S_k/A_k giant images from exact quotient order for k>=5;
- computes the exact quotient image of one point stabilizer per G-orbit, classifying the whole orbit as affected or unaffected;
- when `k > max(8,2+log2(n0))`, checks the Unaffected Stabilizer Theorem conclusion on the exact pointwise stabilizer of all unaffected points;
- for affected G-orbits, checks the exact kernel-orbit bound `|Delta_kernel| <= |Delta|/k` from the Affected Orbits Lemma.

Validation:

- k=5, block size 2, two outside fixed points: the full source group of order 3,840 was independently enumerated; explicit quotient image size 120 and explicit kernel size 32 matched the paired-Schreier certificate exactly.
- synthetic giant actions k=9,12,20 with block size 2 and three outside fixed points were certified without image-group enumeration. The k=20 source group order is **2,551,082,656,125,828,464,640,000**, quotient order is `20! = 2,432,902,008,176,640,000`, and kernel order is `2^20 = 1,048,576` with only 20 returned kernel generators.
- in k=9/12/20, the 2k block-supported points were classified affected and the three outside fixed points unaffected; both the numerical theorem applicability condition and the exact unaffected-stabilizer conclusion held, and every affected-orbit kernel bound was verified.

This is a concrete implementation of the group-theoretic divide-and-conquer prerequisite. It does not yet implement local certificates or Split-or-Johnson, so the general quasipolynomial path remains open.