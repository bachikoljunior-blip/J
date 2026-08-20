from __future__ import annotations

from orbit_factored_string_coset_intersection_v1 import _group_orbits
from permutation_group_schreier import inverse
from s1_structural_classifier_v1 import classify_s1_structure
from signed_johnson_log_codegree_image_si_v1 import (
    signed_johnson_log_codegree_image_candidate_si,
)
from u2_candidate_coset_string_iso_v2 import _translate_subgroup_si_back_to_candidate
from u2_candidate_coset_string_iso_v5 import candidate_coset_string_isomorphism_u5


def candidate_coset_string_isomorphism_u6(
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
    """rev211 candidate SI: compose rev184 Johnson descent through its pair image.

    rev210/v5 is preserved as the first dispatcher, so every already exact terminal,
    imprimitive-family consensus, and rev209 path is unchanged.  If the remaining
    candidate is still transitive primitive-non-giant, rev211 replays only the
    specifically certified rev184 `log-certificate -> codegrees -> Johnson pair`
    path.  Rather than stopping at a second abstract Johnson ground, it solves the
    actual canonical pair-relation string in the induced action, lifts its exact
    coset by the generic paired-action preimage, and resolves the original string
    inside that filter.  Missing gates or unresolved children stay fail-closed.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    H = candidate.subgroup
    n = int(H.degree)
    if len(source) != n or len(target) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    previous = candidate_coset_string_isomorphism_u5(
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
    if classification.status != "primitive_non_giant":
        return previous

    rinv = inverse(candidate.representative)
    subgroup_source = tuple(source[rinv[j]] for j in range(n))
    bridge = signed_johnson_log_codegree_image_candidate_si(
        H,
        subgroup_source,
        target,
        root_n=root_n,
        candidate_dispatch=candidate_coset_string_isomorphism_u6,
        max_test_sets=max_johnson_test_sets,
        max_recognition_nodes=max_recognition_nodes,
        max_johnson_nodes=max_johnson_nodes,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        candidate_group_order_poly_power=group_order_poly_power,
        max_candidate_group_order=max_group_order,
        max_depth=max_depth,
        max_johnson_test_sets=max_johnson_test_sets,
        max_partition_states=max_partition_states,
        family_poly_power=family_poly_power,
        max_family_systems=max_family_systems,
        max_family_quotient_order=max_family_quotient_order,
    )
    if bridge.exact:
        return _translate_subgroup_si_back_to_candidate(
            bridge,
            candidate.representative,
            degree=n,
        )
    return previous


candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u6

__all__ = ["candidate_coset_string_isomorphism_u6", "candidate_coset_string_isomorphism_u2"]
