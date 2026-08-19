# rev93 — remaining-to-remaining lower bound via selected-degree intervals

Root remains **NOT_AGI**.

The next leaf was attacked directly. For every non-anchor source vertex and target candidate, the routine bounds its possible degree to the other selected common vertices even when insertions/deletions are allowed. If `need` vertices are selected from a remaining pool, omitting vertices gives an interval `[max(0,d-omitted), min(d,need-1)]` for the selected internal degree. The gap between the source and target intervals is a lower bound on the number of internal adjacency mismatches incident to that matched vertex.

Summing those interval gaps across matched vertices can count each internal mismatching edge at most twice. Therefore `2 * anchor_mismatches + sum(interval_gaps)` is a sound scaled additive assignment lower bound. Minimizing it with the rev92 min-cost matcher yields a total disagreement lower bound valid for partial matching, not just full bijections.

Validation after one test-driven correction: the first implementation locally screened degree-gap candidates before the global solve; this obscured the numeric lower-bound certificate in a path-vs-star zero-budget test. The screening was removed so the global optimizer carries all safe costs. Final regression is **7 passed** across rev92+rev93 tests. A path on four vertices versus a four-vertex star is rejected at zero budget even with no anchors; an identical five-vertex star certifies the center mapping while correctly abstaining on symmetric leaves; **180 random partial-matching oracle cases** produced no false forced pair.

This does not exhaust the parent. Degree intervals ignore higher-order structure when degree profiles overlap. The leaf is decomposed into:

- `...cba`: partial-selection selected-degree interval lower bound integrated with the global assignment budget — `solved_v0_1`;
- `...cbb`: add higher-order/spectral/motif or relaxation bounds that remain informative when degree intervals overlap — unresolved;
- `...cbc`: validate and scale the combined lower-bound family on larger multi-bucket partial alignments and adversarial symmetry — unresolved.

Estimated active-node count: **475**, below prediction **512**.
