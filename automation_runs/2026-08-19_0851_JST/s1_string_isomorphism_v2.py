from __future__ import annotations

from math import log2

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity
from proof_carrying_si_v1 import ProofCarryingCoset
from proof_carrying_small_order_si_v1 import exact_small_order_group_string_isomorphism
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from s1_string_isomorphism_v1 import s1_string_isomorphism as s1_string_isomorphism_v1


def _monochromatic_terminal(group, source, target, *, root_n):
    n = group.degree
    if n < 1 or not source or not target:
        return None
    if not all(value == source[0] for value in source):
        return None
    if not all(value == target[0] for value in target):
        return None
    if source[0] != target[0]:
        return None

    local_bound = 4.0 * log2(max(2, n)) + 10.0
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="monochromatic_group_si_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=True,
        reason="both strings are the same single color, so every represented group element is an isomorphism",
    )
    return ProofCarryingCoset(
        "exact_monochromatic_group_coset",
        RightCoset(group, identity(n)),
        "monochromatic_group_si_terminal",
        root_n,
        n,
        True,
        True,
        True,
        local_bound,
        True,
        (),
        accounting,
        0,
        "equality scans certified both strings monochromatic with the same value; the exact SI set is the full represented group",
    )


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
    """S1 with exact monochromatic and proof-carrying small-order terminals.

    The monochromatic terminal is a cross-cutting exact shortcut: when both
    strings have the same single color, the full represented group is the SI
    coset, independent of degree or group order.  Otherwise rev163's certified
    group-order terminal is attempted before the existing structural S1 dispatcher.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if root_n is None:
        root_n = n
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")

    mono = _monochromatic_terminal(group, source, target, root_n=root_n)
    if mono is not None:
        return mono

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
