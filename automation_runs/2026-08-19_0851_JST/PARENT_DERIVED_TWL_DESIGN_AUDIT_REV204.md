# rev204 parent-derived exact k-WL/Design provenance audit

Run identity: `chatgpt-session-immediate-20260820T085307+0900-06aca83f`  
Execution start: `2026-08-20T08:53:07+09:00`  
Session starting main: `06aca83ffef7e644ae63421514cfab8c2fe0c2ea`  
AGI-GI transition: `rev203 -> rev204`

## Scope and strict status

rev193 already implements an exact complete first-successful-level `k`-WL/Design witness family on a supplied colored subset relation. rev202 and rev203 derive that relation from a parent bipartite incidence graph and separate its unique-large-relation-twin recursion. rev204 connects these components so the Design input is no longer justified by a caller assertion.

This result is not an ambient transporter for the witness family, a selection of corresponding source/target witnesses, full parent-string isomorphism, recurrence closure, or AGI. `AGI = NOT_AGI`; the root remains unresolved.

Problem count remains **predicted 512 / effective 512**. This replaces H6-R3c1 in place, so no count-overrun rewrite is triggered.

## Existing-world object and cross-layer reuse

The existing-world proof object is the second half of Proposition 5.7 in Helfgott/Bajpai/Dona, arXiv:1710.04574: after the exact derived `d`-ary relation has no twin class larger than half, apply Weisfeiler-Leman and the Design Lemma. The repository already contains the exact correlated-replacement `k`-WL implementation and complete `<=k-1` individualization family from rev193.

rev204 reuses rather than duplicates that machinery:

1. **Parent provenance:** recompute rev202 and rev203 directly from each source/target incidence graph.
2. **Branch exclusion:** enter Design only when both exact outcomes are `relation_twin_no_large_class`; the unique-large-class recursive case is not processed twice.
3. **Exact palette:** reconstruct the complete relation-color sequence in canonical `combinations(range(n),k)` order from proof-carrying relation classes.
4. **Unary boundary:** for `k=1`, reconstruct cells in exact integer relation-color order (not the label-dependent display order of twin classes); corresponding cells are an exact `1/2`-bounded partition and no inapplicable Design gate is invoked.
5. **Higher-arity boundary:** for `k>=2`, call the rev193 complete first-successful-level paired exact `k`-WL/Design family with `alpha=2/3`.
6. **Exact incompatibility:** propagate parent relation status/inventory mismatches and rev193 witness-family invariant mismatch as exact-empty structural results.
7. **Resource boundary:** subset, tuple-state, individualization-state, rounds, and work caps remain typed undetermined outcomes; no resource failure is promoted to a theorem result.
8. **Completeness boundary:** `structural_family_complete` means the complete local witness family is retained. It does not mean a full isomorphism coset has been computed.
9. **Cell-correspondence boundary:** rev193 stores point/component cells in a display order sorted partly by vertex labels. rev204 never treats that order as a source/target correspondence. H6-R3c2 must re-materialize stable color-ID-keyed cells (or extend the witness certificate) before invoking a partition transporter, while retaining every invariant-compatible witness pair.

## Solved child and remaining decomposition

Solved local child:

> Feed the mechanically parent-derived no-large-twin relation into the exact complete `k`-WL/Design witness-family implementation, including the unary direct-partition boundary.

Remaining active internal leaves:

- **H6-R3c2a — color-keyed witness enrichment:** re-materialize stable point/pair color-ID-keyed structures; never use label-sorted display cells as corresponding ordered cells.
- **H6-R3c2b — complete witness pairing:** retain the Cartesian product inside every invariant-compatible source/target witness bucket, subject only to an explicit fail-closed pair cap.
- **H6-R3c2c — witness-family ambient transport:** compute the union of exact parent-group transporter cosets for all enriched witness pairs.
- **H6-R4 — ambient structural transport:** lift degree partitions, relation restrictions, Johnson coordinates, and Design witnesses into exact parent-group transporter cosets.
- **H6-R5 — full-string integration:** intersect every structural transporter with complete source/target incidence strings and return exact empty/coset results.
- **H6-C1 — recurrence closure:** attach multiplicative cost and strict progress certificates to every structural branch.

The next unresolved leaf is **H6-R3c2a, color-keyed enrichment of the first-successful-level Design witness family before any transporter call**.

## Verification

Command:

```text
python -m pytest -q test_derived_relation_twl_design_provenance_rev204.py
```

Expected verified cases include parent-derived cycle-5 UPCC, two-triangle imprimitive split, relabeling invariance, unary direct partition, equal-size unary cells paired by relation color rather than labels, unique-large-class branch exclusion, and resource fail-closed behavior. The definitive result is recorded only after repository CI executes the integrated dependency stack.
