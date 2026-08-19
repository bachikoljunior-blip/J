from __future__ import annotations

from collections import Counter
from math import log2

from johnson_ground_signature_split_si_v2 import johnson_ground_signature_split_string_isomorphism_v2
from permutation_group_schreier import inverse
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from u2_candidate_coset_string_iso_v2 import (
    _parent,
    _translate_subgroup_si_back_to_candidate,
    candidate_coset_string_isomorphism_u2,
)


def _monochromatic_candidate_terminal(candidate, source, target, *, root_n):
    n = candidate.subgroup.degree
    if n < 1 or not source or not target:
        return None
    if not all(value == source[0] for value in source):
        return None
    if not all(value == target[0] for value in target):
        return None
    if source[0] != target[0]:
        return None
    local = 4.0 * log2(max(2, n)) + 12.0
    accounting = RecurrenceAccountingNode(
        n=root_n, m=n, operation_kind="monochromatic_candidate_si_terminal",
        canonical=True, cost_certified=True, local_log2_cost_bound=local,
        children=(), terminal_certified=True,
        reason="both strings are the same single color; every element of the represented candidate right coset is an isomorphism",
    )
    return ProofCarryingCoset(
        "exact_monochromatic_candidate_coset", candidate,
        "monochromatic_candidate_si_terminal", root_n, n,
        True, True, True, local, True, (), accounting, 0,
        "constant-value scans prove the exact SI intersection equals the entire candidate H*r without group enumeration",
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
    """U2 plus exact monochromatic and large-ground Johnson W1 branches.

    The candidate-level monochromatic terminal is representation-independent and
    exact for every H*r.  Otherwise U2 remains the substrate for small-order,
    intransitive, imprimitive, and small-ground Johnson cases.  Only U2's typed
    `undetermined_johnson_ground_cap` leaf is intercepted for the complement-safe
    ground-incidence split.  Homogeneous signed-ground relations remain typed
    unresolved W1 cases.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = candidate.subgroup.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/coset degree mismatch")
    try:
        Counter(source)
        Counter(target)
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc

    mono = _monochromatic_candidate_terminal(
        candidate, source, target, root_n=root_n
    )
    if mono is not None:
        return mono

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
