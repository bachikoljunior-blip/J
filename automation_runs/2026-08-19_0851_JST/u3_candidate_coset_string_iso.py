from __future__ import annotations

from collections import Counter

from johnson_ground_signature_split_si_v2 import johnson_ground_signature_split_string_isomorphism_v2
from permutation_group_schreier import inverse
from u2_candidate_coset_string_iso_v2 import (
    _parent,
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
    max_johnson_recognition_nodes: int = 500000,
    max_johnson_partition_states: int = 200000,
):
    """U2 plus the first proof-carrying large-ground Johnson relational branch.

    U2 remains the exact substrate for small-order, intransitive, imprimitive, and
    small-ground Johnson cases.  Only its typed `undetermined_johnson_ground_cap`
    leaf is intercepted.  There the exact H*r coordinate translation is repeated,
    the rev176 complement-safe ground-incidence split is attempted on H, and an
    exact subgroup result is translated back to the original candidate fiber.
    Homogeneous signed-ground relations remain typed unresolved W1 cases.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    if len(source) != candidate.subgroup.degree or len(target) != candidate.subgroup.degree:
        raise ValueError("string/coset degree mismatch")
    try:
        Counter(source)
        Counter(target)
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc

    base = candidate_coset_string_isomorphism_u2(
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
    if base.exact or base.status != "undetermined_johnson_ground_cap":
        return base

    n = candidate.subgroup.degree
    rinv = inverse(candidate.representative)
    subgroup_source = tuple(source[rinv[j]] for j in range(n))
    split = johnson_ground_signature_split_string_isomorphism_v2(
        candidate.subgroup,
        subgroup_source,
        target,
        root_n=root_n,
        max_recognition_nodes=max_johnson_recognition_nodes,
        max_partition_states=max_johnson_partition_states,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
    )
    if split.exact:
        return _translate_subgroup_si_back_to_candidate(
            split, candidate.representative, degree=n
        )
    return _parent(
        root_n=root_n,
        degree=n,
        status=split.status,
        coset=None,
        exact=False,
        children=(split,),
        cost_certified=False,
        reason="certified large-ground Johnson candidate reached W1 signed-ground incidence recursion, but the current relation remained homogeneous or a bounded structural child was unresolved",
    )
