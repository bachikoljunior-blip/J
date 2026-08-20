from __future__ import annotations

from permutation_group_schreier import inverse
from primitive_giant_color_terminal_v1 import primitive_giant_color_string_isomorphism_terminal
from u2_candidate_coset_string_iso_v2 import (
    _translate_subgroup_si_back_to_candidate,
    candidate_coset_string_isomorphism_u2,
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
    """U2 plus the exact A_n/S_n color terminal for a top-level candidate.

    Existing U2 logic remains authoritative for all previously solved cases.  If
    and only if U2 stops at its typed exact primitive-giant structural leaf, this
    wrapper shifts the source into subgroup coordinates, solves SI in the literal
    A_n/S_n subgroup by the polynomial color/parity terminal, and translates the
    exact subgroup coset back to the original right-coset fiber H*r.

    Intransitive U2 children already call `s1_string_isomorphism_v2`; rev208 also
    upgrades that executor, so primitive giant orbit images are terminalized there
    without duplicating the U2 orbit/preimage machinery.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    result = candidate_coset_string_isomorphism_u2(
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
    if result.exact or result.status != "undetermined_primitive_giant_local_certificates":
        return result

    r = candidate.representative
    rinv = inverse(r)
    subgroup_source = tuple(source[rinv[j]] for j in range(candidate.subgroup.degree))
    inner = primitive_giant_color_string_isomorphism_terminal(
        candidate.subgroup,
        subgroup_source,
        target,
        root_n=root_n,
    )
    return _translate_subgroup_si_back_to_candidate(
        inner,
        r,
        degree=candidate.subgroup.degree,
    )


# Keep the common call-site name for future integrations.
candidate_coset_string_isomorphism_u2_rev208 = candidate_coset_string_isomorphism_u3

__all__ = [
    "candidate_coset_string_isomorphism_u3",
    "candidate_coset_string_isomorphism_u2_rev208",
]
