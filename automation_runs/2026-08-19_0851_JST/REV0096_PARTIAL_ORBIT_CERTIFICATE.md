# rev96 — bounded partial-edit symmetry/orbit certificate

Root remains **NOT_AGI**.

Resolved child `...c2d3b2b2b3c2` at `solved_v0_1` with bounded exact-attribute partial-alignment enumeration.

Let `k = ceil((n+m-U)/2)` be the minimum common cardinality implied by the unmatched-vertex budget `U`. Enumerating feasible mappings of exactly `k` pairs is sufficient for forced-pair semantics: every larger feasible mapping has a size-`k` submapping that preserves exact attributes, cannot increase edge disagreements, and still respects the unmatched budget. Therefore a pair is globally forced iff it is present in every feasible size-`k` mapping.

The search constructs injective equal-attribute assignments and accumulates common-edge disagreements incrementally. The same verified-witness intersection rule from rev95 applies. If the intersection of any found feasible witnesses becomes empty, no identity is forced and that conclusion is already sound without complete enumeration. If the intersection remains nonempty, pairs are released only after the bounded search completes; state/witness limit exhaustion is fail-closed.

Validation mirrored in-session:

- An 8-cycle against the same cycle plus one inserted isolated vertex (all attributes identical) reaches an empty witness intersection after 3 feasible mappings and certifies no forced identity.
- The repeated-attribute 8-vs-9 inserted case used in rev94 has exactly one feasible size-8 mapping under zero edge disagreement and complete bounded enumeration certifies all 8 mapping pairs.
- A deliberately tiny state limit returns `undetermined_search_limit` with no released pairs.

The remaining symmetry child is `...c2d3b2b2b3c3`: scalable symmetry/orbit reasoning beyond bounded backtracking.

Active problem count remains **475**, below prediction **512**.
