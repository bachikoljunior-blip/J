# rev85 direct attempt — infer partial common-node alignment fail-closed

Root remains **NOT_AGI**.

Implemented a bounded exhaustive consensus search under explicit edit budgets. Candidate matches require exact persistent-attribute equality. The search enumerates every injective partial alignment satisfying a maximum total unmatched-vertex count and a maximum number of adjacency disagreements within the aligned common subgraph. It returns only node pairs present in **every** feasible alignment. If the search state/solution budget is exhausted, it returns no inferred pairs; symmetric ambiguity likewise produces no fabricated alignment.

Cumulative local regression rev75–85: **47 passed**. Bounded tests recover the full common alignment for a permuted graph plus one insertion, return no pairs for a constant-attribute 6-cycle with its 12 automorphisms, reject an impossible attribute inventory, fail closed under a deliberately tiny search budget, and honor a declared common-edge edit budget.

The general leaf remains unresolved because this exhaustive method is exponential and exact-attribute semantics are too restrictive for large/noisy settings. It is decomposed into:

- `...c2d3b2a`: bounded exact-attribute consensus inference with edit budgets and complete enumeration — unresolved pending dedicated validation;
- `...c2d3b2b`: scalable large-graph alignment inference with ambiguity certificates — unresolved;
- `...c2d3b2c`: noise-tolerant attribute compatibility without converting tolerance into false identity — unresolved.

Estimated active-node count after decomposition: **457**, below prediction 512.
