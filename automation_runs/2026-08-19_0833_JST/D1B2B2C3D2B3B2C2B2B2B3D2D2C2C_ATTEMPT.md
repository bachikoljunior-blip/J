# rev77 attempt — scalable screening plus exact/parameterized escalation

Root remains **NOT_AGI**.

Implemented a hybrid attributed-graph equivalence procedure. It first uses the scalable invariant surrogate and independent structural collision audit. Only unresolved matches enter a budgeted exact backtracking stage. The exact stage restricts candidate bijections using continuous-attribute compatibility, degree, neighbor-degree profiles, and all adjacency relations to already mapped vertices, with forward checking after each assignment.

Local cumulative regression for rev75–77: **15 passed**.

Bounded evidence includes a relabeled 180-node sparse graph with unique continuous attributes certified exactly using at most roughly one explored state per vertex, a 44-node symmetric cycle certified within budget, cheap rejection of attribute-changed inputs, and explicit `undetermined_budget_exhausted` behavior when the exact search budget is too small.

The method is exact when it returns `certified_isomorphic_exact` or `certified_nonisomorphic_exact`, but worst-case search remains exponential. Budget exhaustion deliberately does not fabricate a result. This resolves the bounded hybrid-escalation child only; worst-case scalable complete attributed-graph equivalence remains unresolved.

Next leaf: `D1b2b2c3d2b3b2c2b2b2b3d2d2c2d` — approximation/stability bounds for continuous attributes and independent distribution-shift validation.
