from __future__ import annotations

from primitive_giant_color_terminal_v1 import primitive_giant_color_string_isomorphism_terminal
from proof_carrying_small_order_si_v1 import exact_small_order_group_string_isomorphism
from s1_string_isomorphism_v1 import s1_string_isomorphism as s1_string_isomorphism_v1
from s1_structural_classifier_v1 import classify_s1_structure


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
    """S1 with exact small-order and exact singleton-block giant terminals.

    Large represented groups are not enumerated.  After the small-order gate, an
    exact structural classification is used only to recognize the special case in
    which the current action itself is literally A_n or S_n.  That case is solved
    directly by color multiplicity/parity and an exact color-stabilizer coset.
    Other large structural cases continue through the existing fail-closed S1v1
    dispatcher unchanged.
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

    classification = classify_s1_structure(
        group,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
    )
    if classification.status == "primitive_giant_local_certificates":
        return primitive_giant_color_string_isomorphism_terminal(
            group,
            source,
            target,
            root_n=root_n,
        )

    return s1_string_isomorphism_v1(
        group,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        max_depth=max_depth,
    )
