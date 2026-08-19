# rev198 Split-or-Johnson external-theorem audit

Scope: W1R-H6 only. This note does **not** claim full Split-or-Johnson closure, full Babai-style quasipolynomial closure, or AGI.

## Existing-world result checked

Primary/authoritative sources consulted for the current H6 leaf:

- L. Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547, especially Section 7 (Split-or-Johnson) and Section 7.6 (measures of progress): https://arxiv.org/abs/1512.03547
- L. Babai, January 9/14 2017 update describing the corrected recursive call after the original Split-or-Johnson complexity error: https://people.cs.uchicago.edu/~laci/update.html
- H. A. Helfgott, J. Bajpai, D. Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574, Section 5.2: https://arxiv.org/abs/1710.04574

The audited theorem boundary is: a uniprimitive classical coherent configuration admits, at quasipolynomial multiplicative cost, either a canonical constant-factor colored partition or a canonically embedded nontrivial Johnson scheme on a large subset. The corrected analysis treats as major progress a constant-factor reduction of the auxiliary part, or finite structural transitions from clique to UPCC and from UPCC to Johnson without increasing that auxiliary size. The 2017 correction matters: phase names alone are not evidence that the required recursive transition has been implemented correctly.

## Mapping to J

- rev193 mechanically verifies the exact correlated-replacement k-WL / Split-or-UPCC Design boundary and the coherent 2-skeleton.
- rev195 promotes only mechanically proved alpha partitions or exact coherent/Johnson reductions to recurrence progress. A stable non-Johnson UPCC remains typed `requires_full_split_or_johnson`.
- rev196 provides recurrence accounting for finite structural ranks, but after audit it requires `progress_certified=True` from an independent algorithm-specific proof. Therefore `clique`, `UPCC`, and `Johnson` labels alone can never close the recurrence.
- rev197 handles one genuine special case of the unresolved UPCC leaf: individualize every possible root, read its exact stable 2-skeleton subconstituents, and accept progress only when **every** root partition has cells at most `0.9*v`. The all-root family is equivariant and has branch multiplicity exactly `v`.
- rev198 composes the rev197 family with exact ambient partition transport and the existing full-string branch-union SI. Stable k-WL color IDs are assigned from sorted exact signatures, so true color-preserving relation isomorphisms preserve the ordered subconstituent-token classes; the complete source/target root cover therefore has at most `v^2` branches. Resource limits remain fail closed.

## Active unresolved child after rev198

Implement the **corrected general UPCC Split-or-Johnson recursion**, not an incidence-2WL or finite-phase surrogate. In the cases where a one-point subconstituent partition does not give the required constant-factor split and the existing coherent reducer does not expose a Johnson ground, construct the theorem-faithful bipartite descent: maintain the large/small parts and their exact color structure, certify twin/symmetry-defect hypotheses, reduce the small part by a constant factor when the corrected routine requires it, or produce an explicit Johnson embedding. Every recursive edge must carry its own canonicality, exactness, multiplicative-cost, and progress certificate before rev196 accounting may accept it.

Predicted/active problem-count policy remains 512/512 by replacing W1R-H6 internally rather than adding a new active top-level branch. AGI remains `NOT_AGI`.
