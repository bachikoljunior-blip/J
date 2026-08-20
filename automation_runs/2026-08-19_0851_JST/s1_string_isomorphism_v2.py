from __future__ import annotations

from literal_giant_candidate_si_v1 import exact_literal_giant_string_isomorphism
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
    """S1 with exact small-order and literal-natural-giant terminals first.

    The represented group may be easy for two independent reasons before the
    heavier structural dispatcher is needed:

    * its order is small enough for the existing exact enumeration terminal; or
    * on its current natural domain it is literally S_n or A_n, in which case
      rev208's exact color-class transporter reconstructs the whole SI coset in
      polynomial time without a local-certificates recursion.

    The second route is especially useful for invariant-orbit images of an
    intransitive parent candidate: the parent need not itself be S_n/A_n.  Its
    orbit image can be literal giant, and the existing exact orbit-action preimage
    machinery then lifts that solved child, including the kernel, back into the
    parent.  Every other group is delegated unchanged to the prior fail-closed S1
    structural dispatcher.
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

    literal_giant = exact_literal_giant_string_isomorphism(
        group,
        source,
        target,
        root_n=root_n,
    )
    if literal_giant.exact:
        return literal_giant

    return s1_string_isomorphism_v1(
        group,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        max_depth=max_depth,
    )
