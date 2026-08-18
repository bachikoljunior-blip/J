# rev76 attempt — collision detection for scalable attributed-graph surrogate

Root remains **NOT_AGI**.

Implemented an independent fail-closed audit around the scalable 1-WL/RFF attributed-graph kernel. Exact polynomial structural invariants (node/edge counts, degree multiset, connected-component sizes, triangle count, trace(A^4)) are checked whenever the surrogate feature maps agree.

Focused cumulative local tests: **10 passed** (5 rev75 + 5 rev76).

Bounded collision witnesses:
- C6 versus two disjoint triangles: identical 1-WL/RFF surrogate with constant attributes, but differing component and triangle invariants; collision is detected and escalated.
- triangular prism versus K3,3: connected 3-regular 6-node graphs with the same basic 1-WL coloring; triangle invariant detects the collision.
- a true relabeling with matching audit fingerprint is deliberately returned as `undetermined_fail_closed` rather than being declared isomorphic.
- materially different invariant feature maps can safely certify distinction because permutation-equivalent attributed graphs must preserve that invariant map.

This solves only the bounded collision-audit child. It does not make 1-WL complete and does not certify equality when all audited invariants coincide. Next work is the escalation layer that combines cheap screening with exact/parameterized refinement.
