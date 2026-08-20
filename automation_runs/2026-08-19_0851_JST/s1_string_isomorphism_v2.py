from __future__ import annotations

from math import factorial

from primitive_giant_full_action_string_iso_v1 import primitive_giant_full_action_string_isomorphism_terminal
from proof_carrying_small_order_si_v1 import exact_small_order_group_string_isomorphism
from s1_string_isomorphism_v1 import s1_string_isomorphism as s1_string_isomorphism_v1


def s1_string_isomorphism_v2(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 4096,
    max_depth: int = 64,
):
    """S1 with exact small-order and literal full-action giant terminals.

    The small-order terminal remains first for inexpensive exact closure.  If the
    represented n-point group is too large to enumerate but has exact order n! or
    n!/2 (n>=5), rev208 uses the polynomial color-class/parity terminal for the
    literal S_n/A_n action.  This is especially important for invariant-orbit
    children reached from candidate-coset SI: those children no longer stop at a
    typed primitive-giant classification merely because their group order is huge.

    All other cases retain the existing structural S1 dispatcher unchanged.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if root_n is None:
        root_n = n

    small = exact_small_order_group_string_isomorphism(
        group,
        source,
        target,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
    )
    if small.exact:
        return small

    if n >= 5 and group.order in (factorial(n), factorial(n) // 2):
        giant = primitive_giant_full_action_string_isomorphism_terminal(
            group,
            source,
            target,
            root_n=root_n,
        )
        if giant.exact:
            return giant

    return s1_string_isomorphism_v1(
        group,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        max_depth=max_depth,
    )
