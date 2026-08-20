from __future__ import annotations

from math import factorial

from primitive_giant_full_action_string_iso_v1 import primitive_giant_full_action_string_isomorphism_terminal
from primitive_johnson_ground_terminal_v1 import primitive_johnson_ground_string_isomorphism_terminal
from proof_carrying_small_order_si_v1 import exact_small_order_group_string_isomorphism
from s1_string_isomorphism_v1 import s1_string_isomorphism as s1_string_isomorphism_v1
from s1_structural_classifier_v1 import classify_s1_structure
from signed_johnson_ground_profile_partition_si_v1 import signed_johnson_ground_profile_partition_si


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
    max_partition_states: int = 4096,
    max_depth: int = 64,
):
    """S1 with small-order, literal-giant, and validated Johnson terminals.

    After the exact small-order and rev208 literal S_n/A_n terminals, rev209
    inspects the already-existing S1 structural classification.  A primitive
    non-giant action first receives the certified small-ground Johnson terminal;
    if that fails only because a larger relational ground is required, the
    complement-safe rev177 ground-profile terminal is tried.  Exact profile
    results are returned directly without enumerating the represented Johnson
    group.  A nonexact profile result is returned as the stronger typed boundary
    rather than discarding it and reclassifying the same instance.

    Intransitive/imprimitive/other cases retain the existing structural S1
    dispatcher unchanged.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if root_n is None:
        root_n = n
    if max_partition_states < 1:
        raise ValueError("max_partition_states must be positive")

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

    classification = classify_s1_structure(
        group,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
    )
    if classification.status == "primitive_non_giant":
        johnson = primitive_johnson_ground_string_isomorphism_terminal(
            group,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_ground_degree=max_explicit_degree,
        )
        if johnson.exact:
            return johnson

        profile = signed_johnson_ground_profile_partition_si(
            group,
            source,
            target,
            root_n=root_n,
            max_partition_states=min(max_partition_states, max(1, root_n ** 2)),
        )
        return profile

    return s1_string_isomorphism_v1(
        group,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        max_depth=max_depth,
    )
