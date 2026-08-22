# AGI-GI rev283 — corrected Split-or-Johnson recurrence composition

## Scope

Rev283 advances only `W1R-H6/corrected-split-or-johnson/recursive-transition-recurrence-composition`. The independently active rev281 / PR #226 owns the sibling `bipartite-recursive-transition-certificate` leaf and explicitly leaves recurrence composition open. Rev283 does not modify or import that branch-only implementation. Instead it consumes the published structural contract of a corrected-SOJ transition object and revalidates every field needed for recurrence accounting before connecting the transition to the already main-integrated quasipolynomial recurrence verifier.

This revision does not construct a Split-or-Johnson transition, does not integrate the transition into the production caller, does not solve the Johnson branch, and does not claim full Split-or-Johnson closure, GI, or AGI. Root state remains **NOT_AGI**.

## Executable composition boundary

`compose_corrected_soj_small_part_recurrence` accepts only the exact constant-factor auxiliary-part transition shape:

- `status == certified_corrected_soj_small_part_reduction`;
- `transition_kind == small_part_reduction`;
- theorem-input gate, canonicality, exactness, and progress certification are all true;
- the observed multiplicative cost and its certified upper bound are finite, at least one, and the observation does not exceed the bound;
- `1 <= small_size_after < small_size_before <= root_n`;
- `alpha in [2/3,1)` and `small_size_after < alpha * small_size_before` mechanically hold; and
- the transition's `alpha` is no weaker than the configured global recurrence shrink fraction.

The caller must separately assert that the transition's multiplicative-cost upper bound is externally/mechanically certified. Rev283 never turns a numerical field into a cost proof by itself. Once that explicit gate is present, the adapter charges `log2(max_multiplicative_cost)` rather than the observed cheaper cost.

The supplied child must already be a main-integrated `RecurrenceAccountingNode`. Its primary measure may not increase and its auxiliary measure must equal the transition's exact `small_size_after`. A positive branch multiplicity is recorded explicitly. The adapter constructs one parent `aux_shrink` node and immediately submits the whole resulting tree to `validate_quasipoly_recurrence_tree`; a failure anywhere below the new edge remains fail closed.

## Deliberate non-compositions

A certified explicit Johnson embedding is **not** re-labelled as `aux_shrink`. Such a certificate is structural evidence for a later exact Johnson/caller integration and does not by itself establish the recurrence measure required by the main accounting contract.

Likewise, `small_size_after == 0` is not silently normalized to one merely to satisfy the existing recurrence type. If a corrected-SOJ transition terminates the auxiliary problem completely, the caller needs an explicit exact terminal mapping rather than a fabricated positive measure. That boundary remains open.

## Replay and accounting identity

Successful compositions carry a deterministic SHA-256 digest binding the normalized transition snapshot, root measure, child measure and operation kind, branch multiplicity, configured shrink fraction, and charged log2 transition bound. Replay recomputes the full composition and the main recurrence validation, so transition-cost drift, child-accounting drift, or parameter drift is rejected.

## Parallel isolation

The rev283 branch adds only four new problem-state files under its reserved paths. It does not modify PR #226, its branch-only module, rev275 through rev282 sibling paths, CRX1/CRX2/CRX3, state-orbit, proof-carrying-merge, `MAIN.md`, or any sibling claim, PR, branch, or workflow.

The independently owned fresh rev275 record is noncanonical and currently prevents the repository's canonical phase-admission generator from loading the complete registry. Rev283 reserves its exact `attempt_solution` evidence path in the schema-v2 claim but does not fabricate an admitted payload while that shared registry error persists. The draft PR must therefore remain unmerged until canonical evidence can be generated and exact-head validation is green.

## Regression boundary

The focused rev283 suite verifies successful composition and replay, deliberate Johnson rejection, theorem/canonical/exact/progress rechecks, constant-factor arithmetic, global shrink compatibility, explicit cost-certificate gating, upper-bound charging, child-measure agreement, branch multiplicity, inherited recurrence failure propagation, zero-output fail-closed behavior, and replay drift detection. The dedicated workflow also reruns the main recurrence-accounting regression file so the adapter is checked against the actual integrated validator contract.
