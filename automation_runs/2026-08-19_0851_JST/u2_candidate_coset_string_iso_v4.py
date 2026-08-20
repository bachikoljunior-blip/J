from __future__ import annotations

import design_tuple_full_string_union_si_v1 as _design_union
import signed_johnson_log_certificate_design_descent_si_v1 as _log_design_base
import signed_johnson_log_certificate_upcc_si_v2 as _log_design
from candidate_full_accept_terminal_v1 import exact_if_entire_candidate_maps_string
from orbit_factored_string_coset_intersection_v1 import _group_orbits
from permutation_group_schreier import inverse
from s1_structural_classifier_v1 import classify_s1_structure
from u2_candidate_coset_string_iso_v2 import _translate_subgroup_si_back_to_candidate
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3


def _filtered_candidate_dispatch(
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
):
    """Exact cheap acceptance before the existing rev208 candidate dispatcher."""
    accepted = exact_if_entire_candidate_maps_string(
        candidate, source_values, target_values, root_n=root_n
    )
    if accepted.exact:
        return accepted
    return candidate_coset_string_isomorphism_u3(
        candidate,
        source_values,
        target_values,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
    )


def candidate_coset_string_isomorphism_u4(
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
):
    """rev209/210 candidate SI: reuse shared Johnson, log-Design, and UPCC paths.

    Before rev208 fallback this dispatcher first accepts a whole exact candidate
    H*r when it is already contained in String Isomorphism.  For transitive
    primitive-non-giant candidates it then runs the existing Johnson relational
    lift and logarithmic certificate/Design descent.  rev210 additionally reuses
    the later rev197/rev198 full-ground UPCC subconstituent closure when the same
    exact logarithmic relation lands in that typed homogeneous Design state.

    The relation-filter and UPCC branch solvers are temporarily pointed at the
    same cheap exact-candidate filter so both nested paths avoid re-entering this
    Johnson wrapper recursively.  Missing recognition/theorem/resource gates and
    unaccounted theorem-scale UPCC recurrence remain fail-closed.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    H = candidate.subgroup
    n = H.degree
    if len(source) != n or len(target) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    accepted = exact_if_entire_candidate_maps_string(
        candidate, source, target, root_n=root_n
    )
    if accepted.exact:
        return accepted

    if n > 1 and len(_group_orbits(H)) == 1:
        classification = classify_s1_structure(
            H,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
        )
        if classification.status == "primitive_non_giant":
            rinv = inverse(candidate.representative)
            subgroup_source = tuple(source[rinv[j]] for j in range(n))

            old_dispatch = _log_design_base.candidate_coset_string_isomorphism_u2
            old_union_dispatch = _design_union.candidate_coset_string_isomorphism_u2
            _log_design_base.candidate_coset_string_isomorphism_u2 = _filtered_candidate_dispatch
            _design_union.candidate_coset_string_isomorphism_u2 = _filtered_candidate_dispatch
            try:
                bridge = _log_design.signed_johnson_log_certificate_design_descent_si(
                    H,
                    subgroup_source,
                    target,
                    root_n=root_n,
                    max_test_sets=max_johnson_test_sets,
                    max_recognition_nodes=max_recognition_nodes,
                    max_johnson_nodes=max_johnson_nodes,
                    max_partition_states=max_partition_states,
                    polylog_power=polylog_power,
                    max_explicit_degree=max_explicit_degree,
                    candidate_group_order_poly_power=group_order_poly_power,
                    max_candidate_group_order=max_group_order,
                    max_depth=max_depth,
                )
            finally:
                _log_design_base.candidate_coset_string_isomorphism_u2 = old_dispatch
                _design_union.candidate_coset_string_isomorphism_u2 = old_union_dispatch

            if bridge.exact:
                return _translate_subgroup_si_back_to_candidate(
                    bridge,
                    candidate.representative,
                    degree=n,
                )

            if bridge.coset is not None:
                filtered = _filtered_candidate_dispatch(
                    bridge.coset,
                    subgroup_source,
                    target,
                    root_n=root_n,
                    polylog_power=polylog_power,
                    max_explicit_degree=max_explicit_degree,
                    group_order_poly_power=group_order_poly_power,
                    max_group_order=max_group_order,
                    max_depth=max_depth,
                )
                if filtered.exact:
                    return _translate_subgroup_si_back_to_candidate(
                        filtered,
                        candidate.representative,
                        degree=n,
                    )

    return candidate_coset_string_isomorphism_u3(
        candidate,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
    )


candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u4

__all__ = ["candidate_coset_string_isomorphism_u4", "candidate_coset_string_isomorphism_u2"]
