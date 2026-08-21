# AGI-GI rev249 Design child execution proof-DAG cover

## Selected unresolved consumer

rev220 established a reusable execution proof-DAG substrate, while explicitly
leaving its algorithmic consumers unresolved.  The current Design full-string
execution already retains the exact `branch_results` that were executed and an
independent `DesignFullStringChildResourceProof`.  rev249 adds the missing
standalone consumer for that complete child cover.  It does not replay a child
solver and it does not modify the active Design caller.

## Exact fail-closed contract

`validate_design_child_proof_dag_cover` accepts only a complete, exact Design
result whose recorded branch count equals the attached execution proofs.  Every
nonempty cover must retain the already-certified child resource proof with the
same expected and accounted branch counts.

For each executed child, the validator builds the existing proof-DAG artifact and
runs the existing occurrence-expanding DAG validator under the original root.
It then merges stored nodes across Design branches.  A replay-stable identity may
share storage across branches only when its complete proof payload, accounting
payload, and child edges agree exactly; any disagreement is a typed
`cross_branch_proof_identity_payload_collision` failure.

Storage reuse never reduces work.  Every branch contributes its full independently
validated execution-occurrence charge, and the complete branch cover is composed
with log-sum-exp.  That result must equal the pre-existing independent Design child
resource certificate.  Caller work outside the child proofs is supplied separately
as `external_log2_cost_bound` and is composed without hiding or recharging child
work.  The complete result must fit the configured original-root envelope.

An exact upstream-empty cover is accepted as a zero-child proof-DAG cover only when
its caller-external work also fits the root envelope.  Partial covers, missing or
unstable identities, recurrence rejection, tree/DAG charge disagreement, resource
certificate mismatch, identity payload collision, and root-envelope overflow all
remain fail closed.

## Validation

The focused regressions cover:

1. the same stable child identity appearing in two Design branches, with one stored
   node but both executions charged;
2. cross-branch identity reuse with different payloads;
3. a missing execution identity, without solver replay;
4. disagreement between the independent tree and DAG cover charges;
5. partial execution and recorded branch-count mismatch;
6. caller-external work exceeding the original-root envelope; and
7. the exact zero-child cover.

The dedicated workflow runs those tests together with the inherited rev220
proof-DAG regressions and compiles both new files.  A local compatibility run passed
all seven focused tests before publication.

## Parallel safety and remaining boundary

The implementation branch adds only this adapter, its regression file, this audit,
and a dedicated smoke workflow.  It does not modify the rev245 shared Design caller,
rev246 primitive-Johnson operator, rev247 shared-S1 path, rev248 relation-image
solver, `MAIN.md`, another claim, another branch, or another workflow.

This closes one CRX3 algorithmic-consumer boundary: complete Design child covers
can now be checked against the shared execution proof-DAG substrate without replay
or undercharging.  Wiring the adapter into the active shared caller is deliberately
left for a later collision-free integration after the current rev245 work settles.
Corrected Split-or-Johnson, complete W1R-H6, global quasipolynomial String
Isomorphism, practical AGI delivery, and AGI are not established.  State remains
`NOT_AGI`.
