from __future__ import annotations

from dataclasses import replace
from math import log2

from coset_stabilizer_primitives import RightCoset
from orbit_factored_string_coset_intersection_v1 import _group_orbits
from permutation_group_schreier import compose, inverse
from resource_bounded_imprimitive_candidate_si_v1 import (
    resource_bounded_imprimitive_string_isomorphism,
)
from s1_structural_classifier_v1 import classify_s1_structure
from u2_candidate_coset_string_iso_v7 import candidate_coset_string_isomorphism_u7


def _delegate_v7(
    candidate,
    source,
    target,
    *,
    root_n,
    polylog_power,
    max_explicit_degree,
    group_order_poly_power,
    max_group_order,
    max_depth,
    max_johnson_test_sets,
    max_partition_states,
    max_recognition_nodes,
    max_johnson_nodes,
    family_poly_power,
    max_family_systems,
    max_family_quotient_order,
    proof_identity,
):
    return candidate_coset_string_isomorphism_u7(
        candidate,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
        max_johnson_test_sets=max_johnson_test_sets,
        max_partition_states=max_partition_states,
        max_recognition_nodes=max_recognition_nodes,
        max_johnson_nodes=max_johnson_nodes,
        family_poly_power=family_poly_power,
        max_family_systems=max_family_systems,
        max_family_quotient_order=max_family_quotient_order,
        proof_identity=proof_identity,
    )


def _translate_resource_proof(inner, representative, *, degree: int):
    if not inner.exact:
        raise ValueError("resource proof translation requires an exact subgroup result")
    extra_bound = 4.0 * log2(max(2, degree)) + 12.0
    accounting = replace(
        inner.accounting,
        local_log2_cost_bound=inner.accounting.local_log2_cost_bound + extra_bound,
        reason=(
            inner.accounting.reason
            + "; exact fixed right-coset coordinate translation back to H*r"
        ),
    )
    translated = None
    if inner.coset is not None:
        translated = RightCoset(
            inner.coset.subgroup,
            compose(representative, inner.coset.representative),
        )
    return replace(
        inner,
        status="exact_translated_" + inner.status,
        coset=translated,
        accounting=accounting,
        local_log2_cost_bound=inner.local_log2_cost_bound + extra_bound,
        reason=(
            "the resource-bounded subgroup SI result was translated exactly "
            "back to the original candidate right coset H*r"
        ),
    )


def candidate_coset_string_isomorphism_u8(
    candidate,
    source_values,
    target_values,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
    max_johnson_test_sets: int = 200000,
    max_partition_states: int = 4096,
    max_recognition_nodes: int = 500000,
    max_johnson_nodes: int = 500000,
    family_poly_power: int = 2,
    max_family_systems: int = 4096,
    max_family_quotient_order: int = 4096,
    max_imprimitive_quotient_kernel_work: int = 0,
    proof_identity=None,
):
    """rev244 candidate dispatcher with opt-in imprimitive phase admission.

    With no new budget this is exactly rev212/v7.  When a positive budget is
    supplied and the candidate subgroup has one unique canonical nontrivial
    block system, v8 does not enter v7's unreserved quotient recursion.  It
    removes the fixed candidate representative, runs the complete
    resource-bounded quotient/kernel operator, and translates only an exact
    result back to H*r.  A rejected envelope remains fail closed.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    group = candidate.subgroup
    n = int(group.degree)
    if len(source) != n or len(target) != n or len(candidate.representative) != n:
        raise ValueError("string/candidate degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    if max_imprimitive_quotient_kernel_work <= 0 or n <= 1:
        return _delegate_v7(
            candidate,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=group_order_poly_power,
            max_group_order=max_group_order,
            max_depth=max_depth,
            max_johnson_test_sets=max_johnson_test_sets,
            max_partition_states=max_partition_states,
            max_recognition_nodes=max_recognition_nodes,
            max_johnson_nodes=max_johnson_nodes,
            family_poly_power=family_poly_power,
            max_family_systems=max_family_systems,
            max_family_quotient_order=max_family_quotient_order,
            proof_identity=proof_identity,
        )

    if len(_group_orbits(group)) != 1:
        return _delegate_v7(
            candidate,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=group_order_poly_power,
            max_group_order=max_group_order,
            max_depth=max_depth,
            max_johnson_test_sets=max_johnson_test_sets,
            max_partition_states=max_partition_states,
            max_recognition_nodes=max_recognition_nodes,
            max_johnson_nodes=max_johnson_nodes,
            family_poly_power=family_poly_power,
            max_family_systems=max_family_systems,
            max_family_quotient_order=max_family_quotient_order,
            proof_identity=proof_identity,
        )

    classification = classify_s1_structure(
        group,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
    )
    if classification.status != "canonical_imprimitive_block_system":
        return _delegate_v7(
            candidate,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=group_order_poly_power,
            max_group_order=max_group_order,
            max_depth=max_depth,
            max_johnson_test_sets=max_johnson_test_sets,
            max_partition_states=max_partition_states,
            max_recognition_nodes=max_recognition_nodes,
            max_johnson_nodes=max_johnson_nodes,
            family_poly_power=family_poly_power,
            max_family_systems=max_family_systems,
            max_family_quotient_order=max_family_quotient_order,
            proof_identity=proof_identity,
        )

    rinv = inverse(candidate.representative)
    subgroup_source = tuple(source[rinv[index]] for index in range(n))
    inner = resource_bounded_imprimitive_string_isomorphism(
        group,
        subgroup_source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        quotient_order_poly_power=group_order_poly_power,
        max_quotient_image_order=max_group_order,
        candidate_group_order_poly_power=group_order_poly_power,
        max_candidate_group_order=max_group_order,
        max_imprimitive_quotient_kernel_work=max_imprimitive_quotient_kernel_work,
        certified_block_system=classification.block_system,
    )
    if inner.exact:
        result = _translate_resource_proof(
            inner,
            candidate.representative,
            degree=n,
        )
    else:
        status = inner.status
        if not status.startswith("undetermined_candidate_"):
            status = "undetermined_candidate_" + status
        result = replace(
            inner,
            status=status,
            reason=(
                "the candidate coordinate was removed exactly, but the complete "
                "transitive-imprimitive quotient/kernel reservation or execution "
                "remains unresolved; "
                + inner.reason
            ),
        )

    if proof_identity is None:
        return result
    if result.proof_identity is not None and result.proof_identity != proof_identity:
        raise ValueError("candidate proof already carries a different execution identity")
    return replace(result, proof_identity=proof_identity)


candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u8

__all__ = [
    "candidate_coset_string_isomorphism_u8",
    "candidate_coset_string_isomorphism_u2",
]
