from __future__ import annotations

from orbit_factored_string_coset_intersection_v1 import _group_orbits
from permutation_group_schreier import inverse
from proof_carrying_si_v1 import ProofCarryingCoset
from s1_structural_classifier_v1 import classify_s1_structure
from signed_johnson_ground_profile_partition_si_v1 import (
    signed_johnson_ground_profile_partition_si,
)
from u2_candidate_coset_string_iso_v2 import _translate_subgroup_si_back_to_candidate
from u2_candidate_coset_string_iso_v6 import candidate_coset_string_isomorphism_u6


def _wrap_profile_cap(inner):
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
        "candidate coordinate was removed exactly, but the bounded Johnson profile partition orbit remains unresolved; "
        + inner.reason,
    )


def candidate_coset_string_isomorphism_u7(
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
    """rev212 candidate SI: reconnect rev177's exact Johnson profile terminal.

    rev211/v6 remains the first dispatcher.  Its unresolved transitive primitive-
    non-giant remainder is then offered to the already validated complement-safe
    Johnson ground-profile partition solver.  The fixed representative of H*r is
    removed exactly, every exact subgroup result is translated back to H*r, and a
    verified profile filter is solved through v6 before acceptance.  Partition
    orbit exhaustion is preserved as a typed fail-closed boundary.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    H = candidate.subgroup
    n = int(H.degree)
    if len(source) != n or len(target) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    previous = candidate_coset_string_isomorphism_u6(
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
    profile = signed_johnson_ground_profile_partition_si(
        H,
        subgroup_source,
        target,
        root_n=root_n,
        max_partition_states=min(max_partition_states, max(1, root_n ** 2)),
        max_recognition_nodes=max_recognition_nodes,
    )
    if profile.exact:
        return _translate_subgroup_si_back_to_candidate(
            profile,
            candidate.representative,
            degree=n,
        )

    if profile.coset is not None:
        filtered = candidate_coset_string_isomorphism_u6(
            profile.coset,
            subgroup_source,
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
        if filtered.exact:
            return _translate_subgroup_si_back_to_candidate(
                filtered,
                candidate.representative,
                degree=n,
            )

    if profile.status == "undetermined_signed_ground_partition_orbit_limit":
        return _wrap_profile_cap(profile)
    return previous


candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u7

__all__ = ["candidate_coset_string_isomorphism_u7", "candidate_coset_string_isomorphism_u2"]
