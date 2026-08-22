# rev2707 — SOJ parent-filtered result proof-DAG integrity

## Scope

This leaf retries only the file-disjoint post-result integrity boundary after rev2500 correctly retreated on a canonical target-revision collision. It consumes only the public `ParentFilteredGroundResult` shape documented by rev2200. It does not import rev2200, rev2400, rev2500, or rev2600 branch-only implementations and it does not modify `MAIN.md`, recurrence code, shared proof-DAG code, sibling claims, sibling branches, sibling PRs, or sibling workflows.

## Gap closed

The public rev2200 result binds exact-empty/nonempty parent-filtered semantics to a deterministic `result_identity`. rev2707 independently replays that identity and seals the public witness into a deterministic proof DAG so downstream consumers fail closed on hidden empty witnesses, malformed subgroup witnesses, count drift, coercion, or certificate serialization drift.

## Certified construction

`soj_parent_filtered_proof_dag_integrity_v1.py`:

1. Replays the public result identity from its documented fields using canonical JSON and SHA-256.
2. Requires literal `certified/exact/complete == true`, strict integer dimensions/counts, canonical SHA-256 identities, and one of the two exact public statuses.
3. Exact-empty results require `accepted_count == 0`, no representative, and no stabilizer witnesses.
4. Nonempty exact right-coset results validate the representative as a permutation, require a unique canonically sorted stabilizer witness, and prove identity/inverse/composition closure plus cardinality coherence.
5. Builds a deterministic proof DAG linking reduction, semantic binding, child instance, child result, and parent-filtered result identities, plus every nonempty witness.
6. Hashes the canonical DAG into `proof_dag_identity` and replays supplied certificates by rebuilding the whole structure.

## Verification

The focused regression suite has 14 cases covering successful empty/nonempty replay, deterministic identity, source digest tamper, bool-as-int coercion, noncanonical witness order, non-subgroup witnesses, count drift, hidden empty witnesses, and DAG/certificate tampering. The dedicated workflow also runs `py_compile`, canonical parallel-admission previews, sibling-import rejection, and reserved-diff enforcement.

The first natural PR check correctly failed closed because this session's already-abandoned rev2500 predecessor still used a noncanonical compound status string and was therefore considered active by the registry parser. That historical claim has now been normalized to the canonical closed state `abandoned` with `completed_at_jst`; no workflow was rerun manually. This documentation-only follow-up push intentionally causes a fresh natural check against the corrected registry.

## Explicit non-claims

rev2707 does not re-run parent filtering, execute recursive String Isomorphism, alter accounting, lift a result to another domain, close corrected Split-or-Johnson, prove Graph Isomorphism, or establish AGI. State remains `NOT_AGI`.
