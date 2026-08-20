# rev203 right-relation -> exact k-WL Design bridge audit

Run identity: `2026-08-20T09:24:53+09:00__rev201__43a16b622129`  
Execution start: `2026-08-20T09:24:53+09:00`  
Stacked base: rev202 candidate branch  
AGI-GI transition under test: `rev202 -> rev203`

## Scope

rev202 constructs and pairs a nonconstant canonical right `t`-subset relation from a bipartite incidence instance whose degree/color signatures are homogeneous. rev203 addresses the next narrower child of H6-R3c: remove any caller assertion that this relation has a useful coherent/Design continuation and mechanically pass the exact relation itself into the repository's already-verified exact correlated-replacement `k`-WL / Design branch machinery.

Primary literature object: Helfgott-Bajpai-Dona, arXiv:1710.04574, §§2.5 and 5.1–5.2. Their canonical `k`-ary Weisfeiler-Leman refinement sends a configuration to a coherent refinement without losing isomorphisms, and the Design Lemma then yields the alpha-coloring or nontrivial classical coherent-configuration branch after at most `k-1` individualizations. Babai's original quasipolynomial GI framework is arXiv:1512.03547.

This revision does not re-prove those theorems. It composes rev202 with the existing exact implementations `colored_subset_exact_twl_design_v1.py` and `colored_subset_exact_twl_branch_plan_v1.py`, preserving their theorem, symmetry-defect, tuple-state, work and branch-materialization gates.

## Cross-layer composition

1. **Bipartite incidence:** derive the source/target right relation directly from exact adjacency.
2. **Relation provenance:** require rev202 paired higher-arity provenance and identical exact relation-color multiplicities.
3. **Canonical coherent refinement:** feed the complete right relation palettes into exact correlated-replacement `k`-WL rather than a caller boolean.
4. **Design witness family:** exhaust the complete first successful individualization level and accept only alpha-coloring, imprimitive split or UPCC outcomes already certified by rev193.
5. **Branch-cover layer:** reuse the exact branch-plan interface from rev193/194 so later tuple transport can consume a complete witness Cartesian cover.
6. **Fail-closed boundary:** any missing relation, symmetry-defect failure, theorem-parameter failure, resource cap or branch cap returns undetermined; no coherent object is invented.

## Problem-tree effect

Predicted/effective problem count remains **512/512**. H6-R3c is decomposed in place:

- **H6-R3c1 — exact relation -> canonical k-WL/Design branch cover:** implemented by rev203, pending repository CI.
- **H6-R3c2 — large-symmetry / Design-gate residual:** when a nonconstant right relation still fails the symmetry-defect/Design theorem gate, derive an exact twin-class quotient or a canonical proper partition and reconnect it to the bipartite recursion.
- **H6-R4 — ambient paired transport:** compute the exact ambient transporter for structural branches.
- **H6-R5 — full-string integration:** intersect structural candidates with the complete parent incidence/string state.
- **H6-C1 — recurrence closure:** charge every branch/descent edge mechanically.

AGI remains `NOT_AGI`; full W1R-H6, full corrected Split-or-Johnson, global recurrence closure, generality/performance/autonomy criteria and usable AGI delivery remain unclaimed.
