# AGI-GI rev1400 — recursive production execution proof-DAG composition

## Scope

This leaf owns only `w1r-h6/corrected-split-or-johnson/larger-ground-recursive-production-execution-proof-dag` under claim `chatgpt-session-j-rev1400-soj-recursive-production-execution-proof-dag-20260822T161600JST-a8a5b96f`.

It is file-disjoint from rev1300 lineage closure, rev293 Johnson recursive-result lift, rev1100/rev1000/rev900 provenance and replay leaves, homogeneous-block work, CRX scopes, `MAIN.md`, and the shared recurrence/proof-DAG implementation. It consumes only public certificate shapes plus main-integrated proof/accounting contracts; it does not import sibling branch-only implementations.

## Gap closed

The preceding corrected Split-or-Johnson larger-ground chain can certify a Johnson reduction, an exact recursive child-result snapshot, an exact lift back to the parent action, construction-cost provenance, total-cost coherence, main provenance, and a downstream lineage closure. Those certificates alone still do not prove that one concrete recursive child execution is the execution whose result/accounting lineage they name.

rev1400 closes that execution-composition boundary. It:

1. independently replays the complete rev1300 `closure_identity` formula from the public closure tuple;
2. independently replays the rev293 exact child-result identity and result-lift transcript from public fields plus the actual parent source/target strings;
3. requires the rev293 child result, result-lift transcript, dimensions, reduction identity, and exact-empty/nonempty semantics to equal the rev1300 lineage fields;
4. requires an actual `ProofCarryingCoset` child execution with a replay-stable attached identity, exact/canonical result, certified local cost, and matching root/child recurrence measures;
5. compares the concrete nonempty child right coset to the replayed public child snapshot by subgroup order/membership and coset equality, or requires both sides empty;
6. mechanically rechecks the lifted parent representative against the original source/target strings and every lifted stabilizer generator against the target string;
7. wraps the parent-to-child edge as recurrence-v4 `aux_shrink`, charges the lineage-certified construction `log2` cost exactly once at the parent, and delegates full occurrence charging and original-root quasipolynomial-envelope validation to main-integrated `validate_execution_proof_dag`.

The root proof identity includes the lineage closure, result-lift digest, child-result identity, concrete child proof identity, parent-values digest, original root, and an explicit version tag. Reuse therefore saves proof storage only; it cannot erase execution occurrences.

## Fail-closed boundaries

The adapter rejects closure/transcript/result identity drift, unsupported or incomplete outcomes, unstable child identities, child coset disagreement, recurrence-measure disagreement, insufficient constant-factor auxiliary shrink, forged parent transport/stabilizer semantics, non-finite external cost, and any rejection from the shared proof-DAG validator.

It does **not** run recursive String Isomorphism, construct or recognize the Johnson reduction, manufacture a recursive child result, authenticate Git reachability, modify shared recurrence/proof-DAG code, infer that upstream draft PRs are merged, close corrected Split-or-Johnson or GI, or establish AGI. The state remains `NOT_AGI`.

## Verification

The dedicated smoke compiles the new module/test, runs focused success/failure regressions, reruns the main-integrated rev220 proof-DAG tests, rejects imports of rev1300/rev293 branch-only implementation modules, enforces the six reserved paths, and previews/materializes canonical `attempt_solution` and `publish` phase-admission evidence using only the main-integrated admission generator.

## Validation heartbeat

On source head `4dc259905f011701680e19f40a4bbfcda8522958`, the dedicated rev1400 smoke passed after the workflow declared NumPy as the inherited rev220 test-only dependency. The rev1400 focused suite passed 13/13 and the inherited rev220 proof-DAG regression suite completed inside the same green smoke; the earlier inherited-test failure was only `ModuleNotFoundError: numpy`, not an implementation failure.

The dedicated workflow then materialized canonical `attempt_solution` and `publish` evidence. At bot-materialized head `d1f8695cb621b66a416eb13e7b50fee53ced1831`, both evidence records are `admitted: true` with `conflicts: []` against registry source `aabe08d98ad0f51965363ab85be43b15bf7ccc0c`.

This documentation-only reserved-path heartbeat intentionally advances the branch after those bot-created evidence commits so exact-head checks can execute normally without manually approving, cancelling, or rerunning any workflow. No implementation, sibling claim, sibling PR, sibling workflow, shared proof-DAG code, recurrence code, or `MAIN.md` is changed by this heartbeat.
