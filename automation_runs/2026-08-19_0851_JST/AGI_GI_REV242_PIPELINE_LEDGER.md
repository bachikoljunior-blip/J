# AGI-GI rev242: shared Design pipeline admission ledger

## Active-session ownership

- automation run ID: `chatgpt-session-j-rev242-20260821T193402+0900-4e443db1`
- isolated branch: `agi-gi-rev242-pipeline-ledger-session-20260821-1934`
- draft PR: `#170`
- stacked on workflow-validated rev241 head `4e443db19d092aad9a9b26bb15574e4410a3cc3f`
- exact scope: CRX2/c2b2a2i3b

Parallel workers should skip this exact scope while its active marker is fresh.
No unrelated branch, pull request, or workflow is modified or restarted.

## Closure attempted

Before the first correlated t-WL run, reserve one caller-derived,
arbitrary-precision original-root ledger for:

1. every source/target correlated t-WL individualization and refinement;
2. the maximal first-success witness Cartesian materialization;
3. every original-domain tuple transporter;
4. every production full-string child path; and
5. every ambient verification and final union Schreier chain.

The exact first-success witness level and later branch subgroups are not known at
this boundary. The ledger therefore uses input-only worst-case bounds. In
particular, a tuple transporter may emit one subgroup generator per ambient
state/generator edge, and a state-orbit child may emit one generator per
state/candidate-generator edge. The existing rev237 intransitive small-image
path is bounded separately because rev240 preserves it when certified.

The five phase bounds are combined with caller `cap+1` saturation. A rejected
ledger returns before `build_exact_twl_design_branch_plan`, so correlated t-WL
never starts. After admission, every phase-local cap is clipped to its own outer
slice before that phase starts: paired/engine t-WL, branch materialization,
tuple transport, full-string child preflight, and union reconstruction. A larger
caller or engineering cap can therefore stop less work, but cannot authorize
work outside the shared reservation.

After execution, rev232, rev234, rev233, rev235--240, and rev241 proof objects
are linked back into the immutable outer ledger. Their actual run, branch,
orbit, candidate-scan, and union-generator counts are verified and recorded
exactly once. Focused regressions use oversized independent inner caps and
mechanically verify that the production caller passes only the five admitted
outer slices.

## Claims withheld

This revision addresses only c2b2a2i3b after workflow validation. Remaining
CRX1/CRX2 consumers, corrected Split-or-Johnson globally, W1R-H6, the global
quasipolynomial recurrence, and strict AGI acceptance remain unresolved.

AGI state: `NOT_AGI`.
