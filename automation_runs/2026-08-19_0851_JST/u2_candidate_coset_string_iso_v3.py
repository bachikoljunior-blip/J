from __future__ import annotations

from math import factorial

from literal_giant_candidate_si_v1 import exact_literal_giant_string_isomorphism
from permutation_group_schreier import inverse
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
    """rev208 candidate SI: close literal natural A_n/S_n giant fibers first.

    The candidate representative is removed exactly, leaving String Isomorphism
    in its subgroup.  A degree-n subgroup of order n! is S_n and, for n>=5, one
    of order n!/2 is A_n.  Those literal natural actions admit a direct complete
    color-class transporter coset, so they do not need the heavier local-
    certificates recursion.  Every other structural case is delegated unchanged
    to rev162/rev171's v2 proof-carrying dispatcher.
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


# Drop-in name for modules whose v2 global is deliberately monkey-patched by the
# rev208 top-level continuation wrapper.
candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u3


__all__ = ["candidate_coset_string_isomorphism_u3", "candidate_coset_string_isomorphism_u2"]
