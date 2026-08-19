# rev94 — anchorless partial-edit global lower-bound certificate

Root remains **NOT_AGI**.

Resolved child `...c2d3b2b2b3b` at `solved_v0_1` as a sound-but-incomplete anchorless partial-edit certificate.

No identity anchors are assumed. For each vertex, the implementation builds a vector of neighbor counts indexed by exact attribute bucket. A candidate pair is allowed only for equal persistent attributes and receives the L1 distance between these two neighborhood-count vectors.

For any common matching of size `k`, let `S` be the sum of these L1 distances over matched pairs, let `U` be the allowed total unmatched-vertex budget, and let `E` be the number of common-edge disagreements. Every unmatched vertex can affect at most `k` matched-endpoint histogram counts, and every matched-edge disagreement can affect at most two endpoint histogram counts. Therefore every feasible alignment obeys `S <= k*U + 2*E`. This supplies a global, anchorless assignment lower bound.

A min-cost cardinality matching computes the minimum possible `S`. Candidate edges are retained only if some required-cardinality assignment containing that edge still satisfies the global bound. Thus every truly feasible alignment remains inside the candidate graph. If the candidate graph maximum cardinality equals the required cardinality, rev91 SCC essential-edge extraction identifies pairs present in every candidate maximum matching. As before, identities are released only after a complete candidate witness is directly checked against attributes, unmatched budget, and the full common-edge disagreement count.

Validation mirrored in-session:

- Constructed 8-vs-9 case with repeated attributes, one inserted distractor, no pre-existing identity anchor, and zero edge-error budget: the global bound yields a unique feasible full witness and safely certifies forced pairs `(4,4)` and `(6,0)`.
- 800 random graph pairs up to 4x4 were exhaustively enumerated across exact attributes, unmatched budgets, and edge-disagreement budgets. 137 identity pairs were released by the certificate and every released pair was contained in the exhaustive true forced-pair intersection; no unsound release was observed.

This does not solve intrinsic graph symmetry: when multiple automorphic/global alternatives survive the sound candidate constraints, the path abstains. The remaining anchorless child is therefore the explicit symmetry/orbit problem `...c2d3b2b2b3c`.

Active problem count remains **472**, below prediction **512**. Whole-tree transversal/rewrite remains inactive.
