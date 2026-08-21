from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class DesignFullStringChildPreflight:
    status: str
    original_root_degree: int
    original_degree: int
    branch_count: int
    subgroup_orders: tuple[int, ...]
    small_order_gate: int
    work_per_branch_upper_bounds: tuple[int, ...]
    work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    terminal_path_certified: bool
    admitted: bool
    executed_branch_count: int
    permutation_candidates_checked: int
    complete: bool
    reason: str


def design_full_string_child_preflight(
    branches,
    *,
    original_root_degree: int,
    original_degree: int,
    group_order_poly_power: int,
    max_group_order: int,
    max_work: int,
) -> DesignFullStringChildPreflight:
    """Reserve every child whose exact small-order terminal is known up front.

    U2 checks value multiplicities and then tries the exact small-order candidate
    terminal before any structural recursion.  Therefore a branch whose subgroup
    order is within ``min(max_group_order, root**power)`` is guaranteed to stop on
    that exact path.  The terminal's existing mechanical charge is

        log2(|H|) + 12 log2(max(2,n)) + 24,

    so ``|H| * max(2,n)**12 * 2**24`` is its exact integer work envelope.  We
    sum this for the complete branch cover before calling U2 even once.  Larger
    structural branches are deliberately rejected and remain a separate problem.
    """
    frozen = tuple(branches)
    root = int(original_root_degree)
    n = int(original_degree)
    power = int(group_order_poly_power)
    implementation_cap = int(max_group_order)
    cap = int(max_work)
    if min(root, n, power, implementation_cap, cap) <= 0:
        raise ValueError("invalid Design full-string child preflight parameters")
    orders = tuple(int(branch.coset.subgroup.order) for branch in frozen)
    if any(order <= 0 for order in orders):
        raise ValueError("Design child subgroup orders must be positive")
    gate = min(implementation_cap, root ** power)
    root_lift = n <= root
    terminal_path = all(order <= gate for order in orders)
    scale = max(2, n) ** 12 * (2 ** 24)
    per_branch = tuple(order * scale for order in orders)
    total = sum(per_branch)
    admitted = root_lift and terminal_path and total <= cap
    if not root_lift:
        status = "design_full_string_child_original_root_lift_unavailable"
        reason = "the full-string child degree exceeds the original root"
    elif not terminal_path:
        status = "design_full_string_structural_child_preflight_unavailable"
        reason = "at least one branch exceeds the exact small-order terminal gate; structural-recursion preflight remains unresolved"
    elif total > cap:
        status = "design_full_string_child_work_cap_exceeded"
        reason = "the complete small-order child cover exceeds the finite budget before the first child"
    else:
        status = "certified_design_full_string_small_order_child_preflight"
        reason = "every branch is guaranteed to terminate in the exact small-order path and the complete cover fits the finite budget"
    return DesignFullStringChildPreflight(
        status, root, n, len(frozen), orders, gate, per_branch, total, cap,
        root_lift, terminal_path, admitted, 0, 0, False, reason,
    )


def record_design_full_string_child_execution(
    preflight: DesignFullStringChildPreflight,
    children,
    *,
    complete: bool,
) -> DesignFullStringChildPreflight:
    if not preflight.admitted:
        raise ValueError("cannot record children for a rejected preflight")
    frozen = tuple(children)
    if len(frozen) > preflight.branch_count:
        raise ValueError("executed child count exceeds the reserved branch cover")
    if complete and len(frozen) != preflight.branch_count:
        raise ValueError("complete Design child execution omitted a reserved branch")
    checked = sum(int(child.permutation_candidates_checked) for child in frozen)
    permitted = sum(2 * order for order in preflight.subgroup_orders[:len(frozen)])
    if checked > permitted:
        raise ValueError("executed candidate scans exceed the exact small-order reservation")
    return replace(
        preflight,
        executed_branch_count=len(frozen),
        permutation_candidates_checked=checked,
        complete=bool(complete),
    )


__all__ = [
    "DesignFullStringChildPreflight",
    "design_full_string_child_preflight",
    "record_design_full_string_child_execution",
]
