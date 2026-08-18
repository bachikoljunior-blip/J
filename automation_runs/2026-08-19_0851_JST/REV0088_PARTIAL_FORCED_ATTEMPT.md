# rev88 direct attempt — scalable partial-edit forced-pair certificates

Root remains **NOT_AGI**.

Implemented a sound-but-incomplete scalable certificate for exact persistent attributes under insertion/deletion budgets. It computes the maximum exact-attribute matching capacity and identifies a unique/unique attribute pair as forced only when removing that sole compatible match would make it impossible to reach the required minimum number of common nodes. Because necessity alone is not enough if the graph constraints have no feasible solution, the implementation also constructs and directly verifies one graph-consistent witness before releasing any forced identities. If witness construction fails or exceeds the edge-disagreement budget, it returns no identity pairs.

Focused local regression: **4 passed**. An 80-node permuted path plus one inserted distractor certifies all common unique-attribute pairs; duplicate-attribute symmetry releases no pairs; inventory impossibility is rejected; and **700 random small cases** compare every released pair against an independent exhaustive oracle, with no unsound releases observed.

The general scalable partial-edit leaf remains unresolved and is decomposed into:

- `...c2d3b2b2a`: exact-attribute capacity-forced singleton anchors with a directly verified feasibility witness — `solved_v0_1`;
- `...c2d3b2b2b`: structurally forced identities inside duplicate-attribute buckets under partial edits — unresolved;
- `...c2d3b2b2c`: scalable witness search when duplicate buckets require nontrivial combinatorial assignment — unresolved.

Estimated active-node count after decomposition: **463**, below prediction 512. The separate hard-symmetry child and noise-tolerant attribute child remain unresolved.
