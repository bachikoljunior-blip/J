from __future__ import annotations

from math import factorial

from literal_giant_candidate_si_v1 import exact_literal_giant_string_isomorphism
from orbit_factored_string_coset_intersection_v1 import _group_orbits
from permutation_group_schreier import inverse
from s1_structural_classifier_v1 import classify_s1_structure
from signed_johnson_joint_relation_candidate_si_v1 import (
    signed_johnson_joint_relation_candidate_string_isomorphism,
)
from signed_johnson_relation_arity_selector_v1 import (
    adaptive_signed_johnson_relation_candidate_si,
)
from u2_candidate_coset_string_iso_v2 import (
    _translate_subgroup_si_back_to_candidate,
    candidate_coset_string_isomorphism_u2 as _candidate_v2,
)


def candidate_coset_string_isomorphism_u3(
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
    """rev208/209 candidate SI: exact literal giants, then Johnson image shrink.

    rev208 removes the candidate representative and closes natural-domain S_n/A_n
    exactly by direct color-class transporter cosets.

    rev209 reuses earlier W1R substrates rather than creating a parallel Johnson
    solver. For a transitive primitive-non-giant candidate it first tries rev183's
    simultaneous complement-safe lower-arity relation image. If that exact
    composition does not close, rev182 adaptively chooses the strongest single
    strictly-smaller relation arity and retries rev180/181 image/preimage filtering.
    Both routes finish with the unchanged v2 candidate machinery inside the exact
    lifted relation candidate. Only exact compositions are accepted here; otherwise
    the original v2 fail-closed result is returned. This conservatively collapses
    two formerly separate Johnson subbranches into one shared image/preimage path.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    H = candidate.subgroup
    n = H.degree
    if len(source) != n or len(target) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    full = factorial(n) if n >= 5 else 0
    if n >= 5 and H.order in (full, full // 2):
        rinv = inverse(candidate.representative)
        subgroup_source = tuple(source[rinv[j]] for j in range(n))
        inner = exact_literal_giant_string_isomorphism(
            H,
            subgroup_source,
            target,
            root_n=root_n,
        )
        if not inner.exact:
            raise AssertionError("literal A_n/S_n order gate reached a nonexact terminal")
        return _translate_subgroup_si_back_to_candidate(
            inner,
            candidate.representative,
            degree=n,
        )

    initial_orbits = _group_orbits(H)
    if len(initial_orbits) <= 1 and n > 1:
        classification = classify_s1_structure(
            H,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
        )
        if classification.status == "primitive_non_giant":
            rinv = inverse(candidate.representative)
            subgroup_source = tuple(source[rinv[j]] for j in range(n))

            joint = signed_johnson_joint_relation_candidate_string_isomorphism(
                H,
                subgroup_source,
                target,
                root_n=root_n,
                polylog_power=polylog_power,
                max_explicit_degree=max_explicit_degree,
                candidate_group_order_poly_power=group_order_poly_power,
                max_candidate_group_order=max_group_order,
                max_depth=max_depth,
            )
            if joint.exact:
                return _translate_subgroup_si_back_to_candidate(
                    joint,
                    candidate.representative,
                    degree=n,
                )

            adaptive = adaptive_signed_johnson_relation_candidate_si(
                H,
                subgroup_source,
                target,
                root_n=root_n,
                polylog_power=polylog_power,
                max_explicit_degree=max_explicit_degree,
                candidate_group_order_poly_power=group_order_poly_power,
                max_candidate_group_order=max_group_order,
                max_depth=max_depth,
            )
            if adaptive.exact:
                return _translate_subgroup_si_back_to_candidate(
                    adaptive,
                    candidate.representative,
                    degree=n,
                )

    return _candidate_v2(
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


candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u3


__all__ = ["candidate_coset_string_isomorphism_u3", "candidate_coset_string_isomorphism_u2"]
