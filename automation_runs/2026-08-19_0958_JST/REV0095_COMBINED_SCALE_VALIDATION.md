# rev95 — combined structural lower-bound validation and scale test

Root remains **NOT_AGI**.

Target leaf `...cbc` was attacked by integrating two sound lower-bound families at the minimum common-cardinality reduction: an exact-attribute min-cost selected-degree-interval assignment lower bound and the rev94 triangle-motif interval lower bound. Because both lower-bound the same common-edge disagreement count, the combined certificate uses their maximum rather than an unsound sum.

Validation: degree-regular `C6` versus two disjoint triangles gives degree LB 0 and triangle LB 1; 180 random 4x4 multi-attribute-bucket cases were checked against exhaustive subset/permutation enumeration with no lower-bound violation; and a planted 80-vs-84 alignment with eight repeated attribute buckets, four unique unmatched distractors, and 12 common-edge flips was not falsely rejected and completed inside the five-second regression guard. Focused regression: **3 passed**.

This completes `...cbc` at `solved_v0_1`. Together with `...cba` and `...cbb`, the total-budget lower-bound child `...c` is integrated as solved; together with already solved siblings `...a` and `...b`, the positive-budget structural-forcing child `...b2` is integrated as solved at the current bounded level.

Next unresolved sibling from rev89 is `...c2d3b2b2b3`: anchorless duplicate-attribute cases requiring higher-order/global symmetry reasoning. AGI remains un-certified.