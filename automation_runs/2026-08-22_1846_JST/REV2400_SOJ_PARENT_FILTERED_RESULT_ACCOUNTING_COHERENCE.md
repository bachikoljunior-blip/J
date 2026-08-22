# rev2400 corrected-SOJ parent-filtered result/accounting coherence

## Scope

This leaf is a file-disjoint, post-replay compatibility boundary between two independently owned public contracts:

1. a rev2200-style exact parent-filtered Johnson-ground result; and
2. a rev291-style certified larger-ground recursive handoff with one admitted `aux_shrink` recurrence child.

It does not import either sibling branch-only implementation. Both upstream objects must be replay-verified by their owning/replaying boundary before this adapter will accept them.

## Contract

The adapter fail-closes unless the parent-filtered result is literal `certified/exact/complete`, has one of the exact nonempty/empty statuses, carries canonical SHA-256 lineage identities, obeys the candidate/accepted and coset-shape invariants, and exposes a positive conservative filtering `work_bound`.

The recursive handoff must be independently replay-verified, retain its certified Johnson reduction, strictly shrink the positive parent action degree to the Johnson ground, retain a canonical/cost-certified single-child `aux_shrink` recurrence root, and expose the existing finite nonnegative logarithmic reduction charge.

The two snapshots are coherent only when their `reduction_identity` values agree and the rev2200 result action degree is exactly the recurrence child/Johnson-ground measure. Exact-empty and nonempty outcomes remain distinct. The output seals both lineages and both cost quantities into a deterministic SHA-256 coherence identity.

## Accounting boundary

The two upstream quantities intentionally remain in their original units:

- `charged_log2_reduction_cost`: the existing recurrence handoff's logarithmic reduction charge;
- `parent_filter_work_bound`: rev2200's conservative integer filtering work bound.

rev2400 does **not** invent a conversion between those units, add the filter bound into shared recurrence accounting, mutate a proof DAG, or claim the filtering work has already been globally charged. A later integration leaf must decide how that local work is represented in the repository's canonical global accounting substrate.

## Non-interference

The leaf does not discover or construct the Johnson reduction, execute recursive String Isomorphism, rerun rev2200 filtering, lift the filtered ground coset to the pre-Johnson original domain, modify shared recurrence/proof-DAG code, or touch sibling claims/branches/workflows. It establishes no corrected Split-or-Johnson, GI, or AGI completion result. State remains `NOT_AGI`.
