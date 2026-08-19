# rev203 Bipartite Split-or-Johnson implementation contract

Scope: the active W1R-H6 leaf only. This document records the primary-source theorem boundary used to prevent later revisions from replacing the corrected recursion with a weaker heuristic. It does **not** certify the theorem conclusion, full graph/string-isomorphism closure, or AGI.

## Primary-source contract

Audited against H. A. Helfgott, J. Bajpai, D. Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574, Section 5.2, especially Theorem 5.3 and Propositions 5.7–5.8:

- Split-or-Johnson takes a uniprimitive classical coherent configuration and returns either a colored alpha-partition or a large embedded Johnson scheme, canonical relative to a subgroup of quasipolynomial index.
- Bipartite Split-or-Johnson takes `X=(V1,V2;A)` with `|V2| < beta*|V1|`, `2/3 <= beta < 1`, and no V1 twin class larger than `2|V1|/3`; it must return either a colored beta-partition of V1 or a Johnson scheme on at least `beta|V1|` points, again with the stated controlled canonicity cost.
- The proof first exploits exact invariants already present in the bipartite graph. Unequal left degrees can give the desired colored partition. Otherwise a large same-degree left subset with distinct neighborhoods supplies a uniform hypergraph on V2; if that hypergraph is complete, its distinct neighborhoods are already a Johnson scheme.
- For a noncomplete neighborhood hypergraph, a logarithmic/controlled-arity relation on V2 is constructed. Large twin classes in that derived relation permit a recursive restriction of V2; otherwise Weisfeiler-Leman plus the Design Lemma yields either a constant-factor V2 split or a nontrivial coherent configuration on a dominant V2 subset.
- Coherent Split-or-Johnson (Proposition 5.8) either gives a half-partition of the large color class or a smaller bipartite instance with the second part reduced by a factor of two and the required left twin bound.
- Where a noncanonical choice incurs quasipolynomial index cost, the corresponding recursive measure must make constant-factor progress. Cost-free canonical restrictions may make smaller one-step progress, but they cannot be used to hide an unbounded expensive recurrence.

The same paper explicitly notes that the 2015 proof had a nontrivial time-analysis error and that the repaired proof uses the corrected simplified recursion. For J, this means theorem phase names, existence statements, or empirical small-instance success are not sufficient progress certificates.

## Current mechanical coverage

- rev193: exact correlated-replacement k-WL / Design classification and coherent 2-skeleton boundary.
- rev195: promotes only mechanically proved alpha splits or exact coherent/Johnson reductions into recurrence progress.
- rev196: accepts finite structural-rank progress only when an independent algorithm-specific `progress_certified` witness is supplied; phase labels alone fail closed.
- rev197–198: exact special UPCC path when every one-point stable subconstituent partition alpha-shrinks; complete all-root cover is transported through the ambient action and reconstructed against the full string.
- rev199: exact Proposition-5.7-style bipartite input gate for part-size and left symmetry-defect/twin hypotheses.
- rev200: exact right-part restriction gate: for a supplied canonical two-color partition of V2, compute the induced left twin relations and keep only a side whose required symmetry-defect bound is mechanically verified.
- rev201: conservative canonical two-color split using only the invariant predicate of membership in a nontrivial left twin class; it refuses to assign arbitrary canonical colors to individual twin classes.
- rev202: exact left degree partition and the unique alpha-dominant same-color/same-degree cell; the dominant cell is explicitly checked for distinct full neighborhoods before it may feed the uniform-neighborhood hypergraph stage.

## Active next child

Implement the **uniform-neighborhood hypergraph / Johnson-or-derived-relation step** for the rev202 dominant twin-free cell:

1. Normalize the common degree by bipartite complement when it exceeds half of `|V2|`.
2. Construct the set of distinct neighborhoods as a uniform hypergraph on V2 and prove equivariance under the supplied source/target ambient actions.
3. If the hypergraph is the complete `d`-uniform hypergraph, return an explicit Johnson labeling/embedding and connect it to the existing exact Johnson machinery.
4. Otherwise construct the controlled-arity exact relation on V2 from neighborhood containment counts as in Proposition 5.7; prove its color normalization is comparable across source/target instances.
5. Route a large twin class through the exact right-part restriction gate, or route the no-large-twin case through the already proof-carrying Design/coherent descent.
6. Attach exact local cost and recurrence-progress certificates before rev196 may accept the edge.

Any resource cap, failed equivariance check, unproved relation-color correspondence, or missing recurrence charge must remain fail closed.

Problem-count policy remains **512 predicted / 512 active** by replacing W1R-H6 internally rather than adding a new top-level branch. AGI remains **NOT_AGI**.
