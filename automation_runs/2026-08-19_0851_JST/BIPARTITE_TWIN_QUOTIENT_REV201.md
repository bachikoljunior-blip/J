# rev201 paired bipartite twin quotient refinement

Scope: AGI-GI W1R-H6 only. AGI remains `NOT_AGI`.

Predicted/active problem count remains **512/512**. rev201 replaces the next W1R-H6 internal child in place.

## Selected child

rev200 proves numeric progress for a stronger visible-twin subcase, but source/target recursion still needs a label-invariant way to compare the produced twin cells. Choosing cells by their repository vertex numbers would be invalid.

## Existing-world check

The construction follows the standard color-refinement / 1-WL principle on the quotient structure rather than inventing encounter-order labels. Relevant external references include:

- Grohe et al., *Dimension Reduction via Colour Refinement*, arXiv:1307.5697: https://arxiv.org/abs/1307.5697
- Dell, Grohe, Rattan, *Lovász Meets Weisfeiler and Leman*, arXiv:1802.08876: https://arxiv.org/abs/1802.08876

The result is used only as an invariant/refinement mechanism; no claim is made that 1-WL solves the general Split-or-Johnson case.

## Implemented progress

`bipartite_twin_quotient_refinement_v1.py` collapses rev199 exact left/right twin classes to a complete/empty two-sorted quotient and runs source/target **joint** refinement. Every color ID is assigned from the shared exact signature universe, so labels are comparable across the pair rather than depending on encounter order.

- Different final quotient-label multiplicities give an exact non-isomorphism certificate.
- If every final quotient label is unique on both sides, the quotient cell map is forced. The code then verifies exact base color/size data and every quotient adjacency block before certifying the unique quotient mapping.
- If a stable quotient color still contains multiple cells, the routine remains fail closed and does not select an arbitrary pairing.
- Dense bipartite complement normalization preserves the result.

## Next unresolved child

When rev201 uniquely pairs quotient cells, construct the **complete internal-permutation transport family** between paired twin cells, intersect it with the actual ambient permutation/coset action, and pass the surviving exact candidate coset(s) to the existing full-string SI. Ambiguous quotient classes require a bounded canonical branching or deeper corrected Split-or-Johnson recursion; they remain unresolved.
