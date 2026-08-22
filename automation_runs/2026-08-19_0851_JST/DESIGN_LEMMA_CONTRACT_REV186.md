# rev186 external Design-Lemma contract

This note records the existing result that contains the current W1R-H5 homogeneous-design leaf. It is a theorem contract, not an AGI claim.

## Existing result checked

Babai's Design Lemma (as summarized in his ICM 2018 survey, Theorem 10.2) takes a k-ary partition structure on m points with symmetry defect at least 0.1. In m^O(k) time, after individualizing a sequence of at most k-1 vertices, it produces one of: a good canonical coloring, a good canonical equipartition, or a good canonically embedded primitive coherent configuration of rank at least 3. The subsequent Split-or-Johnson step reduces the primitive coherent configuration to a significant split/equipartition or a nontrivial Johnson scheme at quasipolynomial multiplicative cost.

The AGI-GI rev184 path already constrains the aggregated certificate arity to O(log m). Therefore the theorem's m^O(k) multiplicative cost is compatible in shape with a quasipolynomial recurrence, but this repository must still encode and mechanically verify the individualization/canonicity/output and accounting obligations before treating W1R-H5 as closed.

The rev185 exact twin-class certificate mechanically checks the symmetry-defect hypothesis for a complete colored t-subset relation. rev186 pairs that certificate across source/target relations and fail-closes on invariant mismatch or insufficient defect.

## Remaining proof-carrying obligations

1. Enumerate or otherwise represent the at-most-(k-1)-point individualization family with an explicit multiplicative-cost certificate.
2. Canonically refine each individualized relation and certify one of the Design-Lemma output types.
3. Align source/target arbitrary choices without losing the full isomorphism coset.
4. Connect coloring/equipartition outcomes to existing partition recursion and coherent-configuration outcomes to the existing Split-or-Johnson/Johnson machinery.
5. Charge all branches to the existing quasipolynomial recurrence contract and fail closed when a theorem parameter or resource gate is not mechanically certified.

## Problem-tree action

The active/predicted problem count remains 512. rev186 is an in-place refinement of W1R-H5, not a new active child. The next unresolved internal leaf is the proof-carrying individualization/output bridge above.

AGI status: NOT_AGI. Full Design-Lemma closure: not yet certified.

References checked: L. Babai, “Group, Graphs, Algorithms: The Graph Isomorphism Problem,” ICM 2018, Theorems 10.2–10.3; Babai's 2017 graph-isomorphism update; Helfgott–Bajpai–Dona exposition of the quasipolynomial GI algorithm.
