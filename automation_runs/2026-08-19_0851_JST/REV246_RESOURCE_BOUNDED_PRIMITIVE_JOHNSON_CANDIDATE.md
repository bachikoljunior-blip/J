# AGI-GI rev246 — resource-bounded primitive Johnson candidate execution

## Scope

This revision reduces `CRX2/c2b2a2iii2` without touching the active rev245 Design-imprimitive integration.  The rev243 preflight already reserved the complete bounded primitive-Johnson/profile attempt while the later subgroup was still unknown, but deliberately kept `exact_path_certified=False`.  Rev246 supplies the next executable boundary: once the exact child subgroup exists, the canonical S1 classifier must select `primitive_non_giant`, the rev243 envelope must admit the caller's pre-child order/generator bounds before Johnson recognition starts, and the existing signed Johnson profile solver then executes under that exact reservation.

This revision does **not** wire the operator into the shared Design caller.  PR #177 currently owns the adjacent transitive-imprimitive changes in `design_full_string_child_preflight_v1.py`, `design_original_root_pipeline_resource_v1.py`, `design_tuple_full_string_union_si_v1.py`, and `u2_candidate_coset_string_iso_v2.py`; rev246 intentionally changes none of those files.

The root state remains **NOT_AGI**.

## Executable contract

`resource_bounded_primitive_johnson_string_isomorphism` performs the following fail-closed sequence:

1. classify the now-known child with the exact S1 structural classifier and reject every non-`primitive_non_giant` branch;
2. verify that caller-supplied pre-child parent-order, image-order, and generator upper bounds dominate the actual subgroup execution;
3. instantiate the rev243 complete Johnson/profile resource envelope with the same recognition-node, robust-orbital (`128`), partition-state, and original-root gates used by the production profile path;
4. reject before semantic Johnson recognition when that envelope is not resource-admitted;
5. execute the existing `signed_johnson_ground_profile_partition_si` unchanged;
6. attach the immutable envelope to the returned proof, charge the full pre-admitted upper bound, and mechanically verify that observed partition states/actions and the executed `(v,k)` parameter stay inside the reservation.

Resource admission never upgrades a semantic failure to exact SI.  A non-Johnson primitive action, recognition failure, partition-state overflow, significant-but-not-profile-determined filter, or any other existing typed residual remains fail closed.  `production_attempt_admitted` is true only when the structural branch is certified, the semantic lift has certified an actually feasible Johnson parameter, the resource envelope admitted before execution, and the bounded attempt returned with its execution charge linked.

## Exactness and accounting boundary

The wrapper preserves the inner proof's exactness, right coset, terminal flag, recurrence object, proof identity, and local-cost certificate.  It adds resource provenance rather than replacing the semantic proof.  For exact profile terminals, recurrence validation therefore continues to validate the same execution-derived tree as before.

The observable partition execution is checked directly against `partition_state_upper_bound` and `partition_action_upper_bound`.  Recognition/profile/Schreier/lift work is charged conservatively by the complete rev243 `work_upper_bound`; the wrapper does not infer a smaller empirical cost from runtime counters.

## Existing-solution audit

The repository already contains the exact semantic components needed here: Johnson coordinate recognition and generator re-induction, complement-safe signed ground profiles, parity-aware partition transport, and proof-carrying recurrence objects.  A second Johnson solver would duplicate those proofs, so rev246 wraps and resource-links the existing implementation instead.

External practical GI systems such as nauty/Traces provide graph automorphism groups and canonical labels and remain useful as independent differential oracles, but they do not expose this repository's required proof-carrying String-Isomorphism right-coset interface or its caller-derived pre-execution quasipolynomial resource ledger.  The Babai/Helfgott-Bajpai-Dona quasipolynomial framework supplies the theoretical group-theoretic context but likewise does not provide a drop-in execution record matching this codebase's exact resource contract.  No external implementation therefore replaces the integration performed here.

## Regression boundary

The rev246 regression suite covers:

- an induced `J(9,2)` action where the signed-profile path returns an exact nonidentity transporter under the rev243 reservation;
- recurrence validation of that exact result;
- work-cap rejection before the semantic solver is invoked;
- fail-closed rejection when a caller's pre-child order bound understates the actual subgroup;
- partition-orbit cap exhaustion remaining unresolved while still linked to the admitted bounded attempt;
- a primitive non-Johnson degree failing in the resource preflight before the semantic solver is entered;
- inherited rev243 resource and rev212 signed-profile regressions in the dedicated workflow.

## Remaining child

This revision implements an executable resource-bounded primitive-Johnson candidate operator, but it does not close the whole production integration leaf.  The remaining work is the collision-sensitive caller-side complete-cover selection and parent-lift/ledger threading after the active rev245 shared Design integration settles.  That later integration must pass the same pre-reserved bounds into this operator and must not double-charge or silently bypass the outer original-root ledger.
