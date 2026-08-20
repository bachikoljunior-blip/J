from __future__ import annotations

from math import factorial

from permutation_group_schreier import inverse
from primitive_giant_full_action_string_iso_v1 import primitive_giant_full_action_string_isomorphism_terminal
from u2_candidate_coset_string_iso_v2 import (
    _translate_subgroup_si_back_to_candidate,
    candidate_coset_string_isomorphism_u2 as _candidate_v2,
)


def candidate_coset_string_isomorphism_u2(
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
    """rev208 candidate SI dispatcher with an exact literal A_n/S_n terminal.

    An n-point subgroup of S_n with order n! is S_n, while an index-two subgroup
    (n!/2, n>=5) is A_n.  Those literal full-action giant cases do not need the
    heavier local-certificates machinery: string isomorphism is exactly a
    color-class transporter, intersected with parity for A_n.  All other cases
    retain the rev207/v2 fail-closed structural recursion unchanged.
    """
    H = candidate.subgroup
    n = int(H.degree)
    source = tuple(source_values)
    target = tuple(target_values)
    if len(source) != n or len(target) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    if n >= 5 and H.order in (factorial(n), factorial(n) // 2):
        rinv = inverse(candidate.representative)
        subgroup_source = tuple(source[rinv[j]] for j in range(n))
        inner = primitive_giant_full_action_string_isomorphism_terminal(
            H,
            subgroup_source,
            target,
            root_n=root_n,
        )
        if inner.exact:
            return _translate_subgroup_si_back_to_candidate(
                inner,
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


__all__ = ["candidate_coset_string_isomorphism_u2"]
