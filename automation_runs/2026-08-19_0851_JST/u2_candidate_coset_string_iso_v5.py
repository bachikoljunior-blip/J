from __future__ import annotations

from canonical_imprimitive_family_candidate_si_v1 import (
    solve_canonical_imprimitive_family_string_isomorphism,
)
from orbit_factored_string_coset_intersection_v1 import _group_orbits
from permutation_group_schreier import inverse
from proof_carrying_si_v1 import ProofCarryingCoset
from s1_structural_classifier_v1 import classify_s1_structure
from u2_candidate_coset_string_iso_v2 import _translate_subgroup_si_back_to_candidate
from u2_candidate_coset_string_iso_v4 import candidate_coset_string_isomorphism_u4


def _wrap_unresolved_family(inner):
    return ProofCarryingCoset(
        "undetermined_candidate_" + inner.status,
        None,
        inner.operation_kind,
        inner.root_n,
        inner.domain_size,
        inner.canonical,
        False,
        inner.local_cost_certified,
        inner.local_log2_cost_bound,
        False,
        inner.children,
        inner.accounting,
        inner.permutation_candidates_checked,
        "candidate right-coset coordinate was removed exactly, but the canonical imprimitive-family subgroup SI child remains unresolved; "
        + inner.reason,
    )


def candidate_coset_string_isomorphism_u5(
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
):
    """rev210 candidate SI: close canonical minimum-block-system families.

    rev209/v4 is run first unchanged, preserving every already exact terminal and
    Johnson/log-Design bridge.  Its remaining explicit transitive imprimitive
    family status is then handled without choosing one block system by point
    labels: every equally minimum canonical system is processed under polynomial
    family/quotient gates, all exact reconstructions must agree, and only that
    consensus is translated back to the original right-coset candidate.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    H = candidate.subgroup
    n = H.degree
    if len(source) != n or len(target) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    previous = candidate_coset_string_isomorphism_u4(
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
    )
    if previous.exact:
        return previous

    if n <= 1 or len(_group_orbits(H)) != 1:
        return previous

    classification = classify_s1_structure(
        H,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
    )
    if classification.status != "canonical_imprimitive_family":
        return previous

    rinv = inverse(candidate.representative)
    subgroup_source = tuple(source[rinv[j]] for j in range(n))
    inner = solve_canonical_imprimitive_family_string_isomorphism(
        H,
        subgroup_source,
        target,
        classification.block_system_family,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        quotient_order_poly_power=group_order_poly_power,
        max_quotient_image_order=max_family_quotient_order,
        candidate_group_order_poly_power=group_order_poly_power,
        max_candidate_group_order=max_group_order,
        max_depth=max_depth,
        family_poly_power=family_poly_power,
        max_family_systems=max_family_systems,
        max_johnson_test_sets=max_johnson_test_sets,
        max_partition_states=max_partition_states,
        max_recognition_nodes=max_recognition_nodes,
        max_johnson_nodes=max_johnson_nodes,
        candidate_dispatch=candidate_coset_string_isomorphism_u5,
    )
    if not inner.exact:
        return _wrap_unresolved_family(inner)
    return _translate_subgroup_si_back_to_candidate(
        inner,
        candidate.representative,
        degree=n,
    )


candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u5

__all__ = ["candidate_coset_string_isomorphism_u5", "candidate_coset_string_isomorphism_u2"]
