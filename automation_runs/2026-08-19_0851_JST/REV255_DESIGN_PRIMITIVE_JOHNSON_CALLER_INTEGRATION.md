# Rev255 — Design primitive-Johnson caller integration

Rev255 closes the caller boundary left by rev243, rev246, and rev254 without changing the stale rev245/PR #177 branch.

## Contract

The production Design child preflight now chooses a terminal only after the cheaper existing paths have been considered. Small-order, admitted imprimitive quotient/kernel, and admitted complete state-orbit terminals retain priority. Branches still unresolved after those checks are classified; the canonical `primitive_non_giant` subset is passed as one complete selected subcover to the rev254 preflight before any rev246 execution begins.

An admitted rev254 reservation is stored on the child preflight. Each selected branch is then executed by U2 through the rev246 resource-bounded primitive-Johnson operator with the exact reserved parent-order, image-order, generator, recognition, partition, and work limits. U2 preserves the rev246 proof subtype and its execution charge when translating an exact subgroup result back to the candidate right coset.

The full-string caller records primitive-Johnson executions back into the rev254 ledger in branch order. Exact union reconstruction remains fail-closed unless the selected subcover is completely executed and every result carries a production-admitted rev246 charge that fits the prior reservation.

## Original-root resource ledger

The pre-tWL Design pipeline reservation now includes a monotone ambient upper bound for the rev243 primitive-Johnson recognition/profile/partition/original-root-lift work. The later branch-specific rev254 reservation must fit inside this earlier child-phase budget. Resource admission is not treated as semantic Johnson success; classification and exactness are still checked at execution time.

## Non-interference

This revision owns only the rev255 paths in the durable takeover claim. It does not modify, close, rebase, or rerun PR #177 or the stale rev255 branch. Existing imprimitive and state-orbit caller integration is carried forward on current `main` and remains independently selected before primitive-Johnson.

AGI state remains `NOT_AGI`; this revision only closes the resource/selection/execution-ledger boundary for this Design child terminal.
