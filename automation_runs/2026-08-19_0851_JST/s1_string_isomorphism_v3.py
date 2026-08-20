from __future__ import annotations

from literal_giant_candidate_si_v1 import exact_literal_giant_string_isomorphism
from s1_string_isomorphism_v2 import s1_string_isomorphism_v2
from s1_structural_classifier_v1 import classify_s1_structure
from signed_johnson_ground_profile_partition_si_v1 import (
    signed_johnson_ground_profile_partition_si,
)


def s1_string_isomorphism_v3(
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
    max_recognition_nodes: int = 500000,
    max_depth: int = 64,
):
    """S1 with the validated literal-giant and Johnson-profile terminals.

    This composes existing exact solvers at the S1 boundary reached by orbit
    recursion.  rev208's natural-domain A_n/S_n color transporter closes literal
    giant orbit images.  For a remaining primitive non-giant action, rev177's
    complement-safe Johnson ground-profile partition terminal closes exactly the
    profile-determined cases without enumerating the represented group.  A
    resource cap or a non-profile-determined relation stays explicitly unresolved.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if root_n is None:
        root_n = n
    if max_partition_states < 1:
        raise ValueError("max_partition_states must be positive")

    previous = s1_string_isomorphism_v2(
        group,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
    )
    if previous.exact:
        return previous

    giant = exact_literal_giant_string_isomorphism(
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
    if classification.status != "primitive_non_giant":
        return previous

    return signed_johnson_ground_profile_partition_si(
        group,
        source,
        target,
        root_n=root_n,
        max_partition_states=min(max_partition_states, max(1, root_n ** 2)),
        max_recognition_nodes=max_recognition_nodes,
    )


__all__ = ["s1_string_isomorphism_v3"]
