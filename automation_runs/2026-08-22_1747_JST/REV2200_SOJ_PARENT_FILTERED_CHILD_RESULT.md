# rev2200 — SOJ parent-filtered child result binding

## Scope

This leaf closes only the exact parent-filtering boundary left explicit by the Johnson child semantic projection and recursive child-instance execution contracts. It is isolated to rev2200 and does not modify `MAIN.md`, shared S1/proof-DAG/recurrence code, sibling claims, sibling branches, sibling PRs, or sibling workflows.

## Gap closed

The semantic projection contract proves only the safe direction

`parent transporter => child-profile transporter`.

It intentionally does **not** certify the converse. The child-instance execution contract can certify an exact child transporter coset for caller-supplied child strings, but intentionally does not certify that those child strings are semantically equivalent to the parent Johnson string.

rev2200 composes those public contract shapes without importing either sibling branch-only implementation. It independently replays their hash/shape semantics and then filters the exact child transporter set against the complete original parent Johnson string.

## Certified construction

`soj_parent_filtered_child_result_v1.py` performs the following fail-closed checks:

1. Reconstruct the complete canonical `J(v,k)` vertex family and every ground-point star.
2. Recompute parent digests, incident-color child profiles, child digests, and the semantic binding identity.
3. Recompute the recursive child-result identity and child-instance identity from explicit execution context.
4. Independently enumerate the induced-ground group under the explicit `max_group_elements` cap and verify that the claimed child result equals the exact child transporter set in that group.
5. For every exact child candidate, induce its permutation on all Johnson vertices and test the full parent source/target transport equation.
6. Certify either exact empty or reconstruct a single exact right coset of the parent-valid ground permutations, mechanically checking the offset set is exactly a subgroup.
7. Bind the result to the semantic binding identity, child instance/result identities, exact candidate/accepted counts, and an explicit work bound.

Certification fails closed if the generated group exceeds the explicit cap; there is no hidden unbounded enumeration fallback.

## Regression that exercises the missing converse

The focused test suite includes the concrete `J(4,2)` pair

- source: `(0, 0, 1, 1, 0, 0)`
- target: `(0, 1, 0, 0, 1, 0)`

The incident-color semantic projection admits all **24** ground permutations as child transporters, while exact parent filtering retains only **8**. This witnesses why the one-way semantic projection cannot be treated as an equivalence and verifies that rev2200 removes those false positives exactly.

## Explicit non-claims

rev2200 does not discover a Johnson embedding, execute recursive String Isomorphism, import rev1900/rev1700 implementations, lift a ground result to the pre-Johnson original domain, modify recurrence accounting, extend a proof DAG, close corrected Split-or-Johnson, prove Graph Isomorphism, or establish AGI. The repository state remains `NOT_AGI`.

## Local verification

- `python -m py_compile soj_parent_filtered_child_result_v1.py test_soj_parent_filtered_child_result_rev2200.py`
- focused regressions: **9/9 passed**
- tampered semantic identity/profile, tampered child instance identity, false exact child snapshot, noncanonical vertex family, and explicit group-cap exhaustion all fail closed.
