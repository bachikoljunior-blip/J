from __future__ import annotations

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
    """S1 with a proof-carrying small-order group terminal before structure.

    rev163's terminal was degree-gated because it enumerated S_m.  This wrapper
    first asks a stronger question: is the represented group itself small enough
    to enumerate exactly?  If yes, SI is solved directly regardless of degree.
    Otherwise the existing structural S1 dispatcher is invoked unchanged.
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

    return s1_string_isomorphism_v1(
        group,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        max_depth=max_depth,
    )
