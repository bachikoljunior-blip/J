# rev2500 — SOJ parent-filtered result proof-DAG integrity

## Scope

This leaf closes only a post-result integrity boundary for the public `ParentFilteredGroundResult` shape produced by rev2200. It does not import rev2200 or rev2400 branch-only implementations and it does not modify `MAIN.md`, recurrence code, shared proof-DAG code, sibling claims, sibling branches, sibling PRs, or sibling workflows.

## Gap closed

rev2200 certifies an exact parent-filtered result and publishes a deterministic `result_identity`, an empty/nonempty status, and (for the nonempty case) a representative plus the complete parent stabilizer element set. That public result is sufficient for downstream consumers, but a consumer can still accidentally accept a malformed or rehashed witness list, hidden witnesses on an exact-empty result, count/witness drift, or non-deterministic proof serialization.

rev2500 adds an independent, fail-closed integrity adapter around that public result shape.

## Certified construction

`soj_parent_filtered_proof_dag_integrity_v1.py`:

1. Replays the rev2200 public `result_identity` from its documented fields using canonical JSON and SHA-256.
2. Requires literal `certified/exact/complete == true`, strict integer dimensions/counts, canonical SHA-256 identities, and one of the two exact rev2200 statuses.
3. For an exact-empty result, requires `accepted_count == 0`, `representative is None`, and an empty stabilizer witness.
4. For a nonempty exact right coset, validates the representative as a permutation, requires the stabilizer witness to be unique and canonically sorted, proves identity/inverse/composition closure, and requires its cardinality to equal `accepted_count`.
5. Builds a deterministic proof DAG linking reduction, semantic binding, child instance, child result, and parent-filtered result identities. Nonempty results additionally carry the representative and every stabilizer element as deterministic witness nodes.
6. Hashes the entire canonical DAG into `proof_dag_identity`.
7. Replays a supplied certificate by rebuilding the whole DAG from the source result and rejecting any field, edge, witness, or digest drift.

## Explicit non-claims

rev2500 does not re-run the parent filter, prove the semantic child projection, execute recursive String Isomorphism, alter rev2400 accounting, lift the result to another domain, close corrected Split-or-Johnson, prove Graph Isomorphism, or establish AGI. The repository remains `NOT_AGI`.

## Verification

- `python automation_runs/2026-08-22_1851_JST/test_soj_parent_filtered_proof_dag_integrity_rev2500.py`
- `python -m py_compile automation_runs/2026-08-22_1851_JST/soj_parent_filtered_proof_dag_integrity_v1.py automation_runs/2026-08-22_1851_JST/test_soj_parent_filtered_proof_dag_integrity_rev2500.py`
- focused regressions: **14/14 passed locally**
- tampered result identity, bool-as-int coercion, noncanonical witness order, non-subgroup witnesses, cardinality drift, hidden empty witnesses, DAG tamper, and certificate identity tamper all fail closed.
