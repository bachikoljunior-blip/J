# rev210 world-solution / problem-tree audit

## Scope and strict state

This audit is for the J repository AGI-GI rev series only.  It does not use other repositories as progress evidence.  AGI remains **NOT_AGI**: no claim is made that graph/string-isomorphism progress establishes generality, performance, autonomy, or practical AGI delivery.

At the start of this run the latest AGI commit was rev209.  The canonical problem-tree count remains predicted **512** and effective **512**.  rev210 targets an already-existing typed leaf, `canonical_imprimitive_family`, so it replaces that leaf in place rather than adding a new active problem.  No observed effective count exceeded 512 in this run, so the mandatory over-count full-tree rewrite trigger did not fire.

## Existing world solutions checked at multiple layers

Primary references checked again for this run:

1. L. Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547.  The paper explicitly treats String Isomorphism and Coset Intersection together with GI, builds on Luks's permutation-group SI framework, and uses canonical partitioning/local certificates with Johnson structures as the main primitive obstruction.
2. H. A. Helfgott, J. Bajpai, D. Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574.  This gives an independent detailed exposition of the Babai/Luks strategy and its group/coset recursion.
3. D. Wiebking, *Graph isomorphism in quasipolynomial time parameterized by treewidth*, arXiv:1911.11257.  Its multiple-coset isomorphism abstraction is relevant to handling a canonical family of equivalent structural decompositions without collapsing them by a label-dependent arbitrary choice.

### Leaf layer: multiple minimum block systems

The pre-rev210 classifier already returned the *entire* family of equally minimum invariant block systems and explicitly refused to choose one by point labels.  The missing leaf was therefore not block discovery but a family-aware exact SI continuation.

rev210 uses the existing Luks-style block action / quotient / exact preimage / candidate-coset primitives for **every** equally canonical minimum block system.  Each quotient image is polynomially gated before exact enumeration.  Every lifted quotient fiber must close exactly.  Each block system independently reconstructs the full SI right coset, and all reconstructions must agree before the result is accepted.  This removes the label-dependent-choice branch rather than creating a parallel solver tree.

### Parent layer: H6-C2 candidate SI

The family operator is inserted into the same candidate dispatcher already used by rev206 parent execution and rev207 proof replay.  Thus the parent-level solution is shared: exact block quotient/preimage recursion, candidate SI, and proof-carrying recurrence accounting.  rev210 also tightens the accounting semantics: a same-domain quotient fiber may terminate exactly, while a nonterminal quotient fiber must still expose an immediate strictly smaller kernel-orbit partition.  This prevents artificial same-size recursive chains while not rejecting genuine exact terminals.

### Higher W1R-H6 layer

This change deletes one imprimitive-family residual but does **not** solve the remaining primitive barriers.  The shared world-solution direction remains Babai/Luks rather than a new bespoke solver tree: primitive non-giant / Johnson cases should continue through existing Johnson relational lift, lower-arity image/preimage, log-certificate, Design, and Split-or-Johnson machinery; primitive giant cases must continue through exact giant/local-certificates operators.

### Root AGI layer

Existing GI/SI algorithms solve a highly structured algorithmic problem and do not by themselves establish AGI.  They therefore remain a child/substrate result only.  The root criteria require independent empirical evidence for generality, performance, autonomy, and usable delivery; none is inferred from rev210.

## rev210 solved leaf and next exact leaf

Solved if CI validates:

- `H6-C2 / canonical_imprimitive_family`: exact family-wide quotient/preimage SI consensus under polynomial family and quotient gates, with fail-closed behavior otherwise.

Next unresolved leaf after this replacement:

- `H6-C2 / primitive_non_giant / log-certificate Johnson structural descent`: when `signed_johnson_log_certificate_design_descent_si_v1` returns `verified_log_certificate_johnson_structural_descent`, the second recognized Johnson ground is still only structural evidence.  The next implementation must construct the actual second-ground action/relation and compose its exact SI result back through the existing signed candidate machinery with rev207-compatible recurrence accounting.  Missing theorem gates or nonconstructive recognition must remain fail closed.

Other still-open siblings include nonliteral primitive giant/local-certificates continuations and genuinely unresolved corrected Split-or-Johnson states.  They are not claimed solved by rev210.
