from __future__ import annotations

from dataclasses import dataclass
from math import log2

from certified_group_enumeration_v1 import enumerate_schreier_group_exact
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class SmallOrderProofCarryingCoset(ProofCarryingCoset):
    group_elements_checked: int = 0
    certified_group_order: int = 0


def _result(
    status,
    coset,
    *,
    root_n,
    degree,
    exact,
    cost_certified,
    local_bound,
    terminal,
    accounting,
    checked,
    reason,
    group_order,
):
    return SmallOrderProofCarryingCoset(
        status,
        coset,
        "small_order_group_si_terminal" if exact else "small_order_group_cap",
        root_n,
        degree,
        True,
        exact,
        cost_certified,
        local_bound,
        terminal,
        (),
        accounting,
        checked,
        reason,
        group_elements_checked=checked,
        certified_group_order=group_order,
    )


def exact_small_order_group_string_isomorphism(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    group_order_poly_power: int = 2,
    max_group_order: int = 4096,
) -> SmallOrderProofCarryingCoset:
    """Exact SI by enumerating G itself when its certified order is small.

    This is degree-independent.  The Schreier chain first certifies |G|; only if
    |G| is within both root_n^c and a hard implementation cap is generator BFS
    allowed.  Every enumerated group element is tested against the two strings.
    The resulting exact isomorphism set is reconstructed and audited as a right
    coset.  Groups above the cap are returned as typed unresolved leaves without
    performing any element enumeration.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    if root_n < n:
        raise ValueError("root_n must dominate current degree")
    if group_order_poly_power < 1 or max_group_order < 1:
        raise ValueError("invalid small-order terminal parameters")

    allowed_order = min(max_group_order, root_n ** group_order_poly_power)
    if group.order > allowed_order:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, n),
            operation_kind="small_order_group_cap",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason="Schreier-certified group order exceeds the polynomial/implementation enumeration cap",
        )
        return _result(
            "undetermined_group_order_cap",
            None,
            root_n=root_n,
            degree=n,
            exact=False,
            cost_certified=False,
            local_bound=0.0,
            terminal=False,
            accounting=accounting,
            checked=0,
            reason="group order is too large for the proof-carrying exact enumeration terminal; structural recursion remains required",
            group_order=group.order,
        )

    elements = enumerate_schreier_group_exact(group, max_elements=allowed_order)
    if elements is None or len(elements) != group.order:
        raise AssertionError("small-order gate admitted the group but exact enumeration did not match its certified order")

    matches = tuple(
        g for g in elements
        if all(source[i] == target[g[i]] for i in range(n))
    )
    checked = len(elements)
    local_bound = log2(max(1, group.order)) + 12.0 * log2(max(2, n)) + 24.0
    if local_bound + 1e-12 < log2(max(1, checked)):
        raise AssertionError("small-order terminal charge does not dominate executed group scan")

    if not matches:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, n),
            operation_kind="small_order_group_si_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="complete enumeration of the Schreier-certified group found no string isomorphism",
        )
        return _result(
            "exact_empty_small_order_group",
            None,
            root_n=root_n,
            degree=n,
            exact=True,
            cost_certified=True,
            local_bound=local_bound,
            terminal=True,
            accounting=accounting,
            checked=checked,
            reason="all elements of the exact represented group were tested and none maps the source string to the target",
            group_order=group.order,
        )

    witness = min(matches)
    translated = tuple(compose(inverse(witness), p) for p in matches)
    subgroup = schreier_stabilizer_chain(translated or (identity(n),))
    result = RightCoset(subgroup, witness)
    if subgroup.order != len(matches):
        raise AssertionError("translated string-isomorphism set did not reconstruct the expected subgroup order")
    if any(not result.contains(p) for p in matches):
        raise AssertionError("reconstructed small-order SI coset lost an enumerated isomorphism")

    reconstructed = tuple(g for g in elements if result.contains(g))
    checked += len(elements)
    if reconstructed != matches:
        raise AssertionError("reconstructed small-order SI coset differs from exact enumerated matches")
    if local_bound + 1e-12 < log2(max(1, checked)):
        raise AssertionError("small-order terminal charge does not dominate reconstruction audit")

    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="small_order_group_si_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=True,
        reason="complete exact group enumeration and second-pass coset reconstruction audit are the terminal proof",
    )
    return _result(
        "exact_small_order_group_coset",
        result,
        root_n=root_n,
        degree=n,
        exact=True,
        cost_certified=True,
        local_bound=local_bound,
        terminal=True,
        accounting=accounting,
        checked=checked,
        reason="the exact string-isomorphism set inside the represented group was enumerated and reconstructed as one right coset",
        group_order=group.order,
    )
