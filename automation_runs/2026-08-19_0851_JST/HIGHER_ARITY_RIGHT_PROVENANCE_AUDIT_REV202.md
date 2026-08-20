# rev202 higher-arity right-relation provenance audit

Run identity: `2026-08-20T09:24:53+09:00__rev201__43a16b622129`  
Execution start: `2026-08-20T09:24:53+09:00`  
Session starting main: `43a16b622129308661fc20ca40f447ecb1f87d62`  
AGI-GI transition under test: `rev201 -> rev202`

## Scope and strict status

rev201 solved H6-R3a only for a proper right partition exposed by exact degree/input-color signatures. Its fail-closed residual is the case where every right vertex has one first-order signature. rev202 attacks exactly that residual.

The new object is an exact colored relation on unordered right `t`-subsets. A subset is colored by (1) its right-input-color multiset and (2), for each canonical left input color, the histogram of left vertices having exactly `j` neighbors in the subset for `j=0..t`. Internal ordering of the subset never enters the color. Therefore every color-preserving bipartite isomorphism preserves this relation color exactly.

`AGI = NOT_AGI`. Full corrected Bipartite Split-or-Johnson, coherent closure, ambient transport, full-string isomorphism, global recurrence closure, generality/performance/autonomy evidence, and usable AGI delivery are not claimed.

Problem-count policy remains **predicted 512 / effective 512**. H6-R3b replaces the current active subleaf in place; no new active branch is counted.

## Existing-world object and cross-layer mapping

The construction is deliberately a conservative implementation of objects already used in the corrected graph-isomorphism literature rather than a new theorem claim.

Primary references:

- H. A. Helfgott, J. Bajpai, D. Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574, especially §5.1 Design Lemma and §5.2 Bipartite/Coherent Split-or-Johnson: https://arxiv.org/abs/1710.04574
- L. Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547: https://arxiv.org/abs/1512.03547

Relevant existing ideas and the rev202 mapping:

1. **Hypergraph/relation layer.** Helfgott explicitly treats colored complete uniform hypergraphs and higher-arity coherent configurations. rev202 turns the homogeneous bipartite residual into a complete colored `t`-subset relation on the right side.
2. **Canonical-choice layer.** The Split-or-Johnson exposition requires functorial/canonical structures. rev202 selects the *first* informative arity `t=2,3,...` and uses typed color encodings plus exact multiplicities; vertex labels never decide the relation color or selected arity.
3. **Design layer.** Pair codegrees can remain homogeneous while a higher-order design statistic is informative. The Fano-plane incidence regression demonstrates the intended boundary: all right blocks have equal degree and all right pairs have equal intersection, but triple occupancy colors are nonconstant, so the first informative relation occurs at arity 3.
4. **Coherent/WL layer.** In the corrected Split-or-Johnson proof, a nontrivial higher-arity/Design object is subsequently refined into coherent structure before recursive use. rev202 stops before that step; H6-R3c remains responsible for turning the nonconstant relation into a proof-carrying coherent parent object without caller-supplied truth flags.
5. **Exact paired-provenance layer.** Source and target compare the exact relation-color inventory at every tested arity. Any mismatch is a necessary-invariant failure and is returned as exact non-isomorphism evidence for the color-preserving bipartite problem.
6. **Complexity layer.** The default arity cap is `ceil(log2(|V2|))`, and each arity has an explicit subset-enumeration cap. Exceeding it fails closed rather than silently violating the quasipolynomial accounting discipline.

## Attempt result and decomposition

Target leaf:

> **H6-R3b — higher-arity right-relation provenance for the homogeneous degree/color residual.**

Implemented child:

- exact unordered `t`-subset relation from left-color-stratified adjacency-count histograms;
- first informative arity selection;
- exact source/target relation-color multiplicity comparison;
- pair-informative, Fano triple-informative, homogeneous no-progress, cap, unsupported-color and exact-mismatch regressions;
- exhaustive `4! x 4! = 576` left/right relabeling regression for the pair-informative case.

If repository CI confirms the implementation, H6-R3b is locally solved and the next unresolved leaf is:

> **H6-R3c — coherent provenance:** from a nonconstant canonical right relation, construct/refine the parent coherent configuration and certify that the derived color classes/relations are canonical for the paired source/target instance, without caller booleans; otherwise fail closed.

Following leaves remain H6-R4 ambient paired transport, H6-R5 full-string integration, and H6-C1 recurrence closure.

## Verification boundary

Before PR CI, only syntax/interface-compatible local preflight was performed. Repository success must be established by the dedicated `rev202 higher-arity right provenance smoke` workflow (and, if run, the broader AGI-GI rev validation) before the branch is merged or H6-R3b is recorded as solved on main.
