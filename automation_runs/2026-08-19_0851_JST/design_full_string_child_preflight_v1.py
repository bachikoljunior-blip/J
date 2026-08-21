from __future__ import annotations

from dataclasses import dataclass, replace

from local_certificate_preimage_resource_v1 import _chain_bound
from orbit_factored_string_coset_intersection_v1 import _group_orbits, _image_chain


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
    terminal_kinds: tuple[str, ...] = ()
    orbit_image_orders: tuple[tuple[int, ...], ...] = ()
    permutation_scan_upper_bounds: tuple[int, ...] = ()


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
    sum this for the complete branch cover before calling U2 even once.  For an
    intransitive larger parent, the preflight also constructs every canonical
    initial orbit image before the first child.  If all those exact image orders
    pass the same terminal gate, it reserves their enumeration plus image-chain,
    paired-kernel and full-domain preimage work.  A later subgroup cannot increase
    an orbit image order.  Transitive and nested-structural images remain separate
    fail-closed problems.
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
    terminal_kinds = []
    orbit_image_orders = []
    scan_bounds = []
    per_branch = []
    terminal_path = True
    scale = max(2, n) ** 12 * (2 ** 24)
    for branch, order in zip(frozen, orders):
        if order <= gate:
            terminal_kinds.append("small_order")
            orbit_image_orders.append(())
            scan_bounds.append(2 * order)
            per_branch.append(order * scale)
            continue

        group = branch.coset.subgroup
        orbits = _group_orbits(group)
        if len(orbits) <= 1:
            terminal_path = False
            terminal_kinds.append("unresolved_structural")
            orbit_image_orders.append(())
            scan_bounds.append(0)
            per_branch.append(0)
            continue

        images = tuple(_image_chain(group, orbit) for orbit in orbits)
        image_orders = tuple(int(image.order) for image in images)
        orbit_image_orders.append(image_orders)
        if any(image_order > gate for image_order in image_orders):
            terminal_path = False
            terminal_kinds.append("unresolved_nested_structural_image")
            scan_bounds.append(0)
            per_branch.append(0)
            continue

        # S1 first classifies the parent, then for every canonical orbit builds
        # the current image, solves its small-order terminal, and constructs the
        # paired kernel/preimage.  Later current groups are subgroups of the
        # initial branch group, hence their orbit-image orders cannot exceed the
        # exact initial image orders certified above.  The bound deliberately
        # charges a second full-domain orbit/classification pass because this
        # preflight audit is separate from the actual S1 execution.
        g = max(1, len(group.original_generators))
        audit = 2 * (8 * n * n * max(g, order) + _chain_bound(n, g, order, n, 10**1000))
        work = audit
        scans = 0
        for orbit, image_order in zip(orbits, image_orders):
            m = len(orbit)
            image_chain = _chain_bound(m, g, order, m, 10**1000)
            child = image_order * (max(2, m) ** 12) * (2 ** 24)
            paired = _chain_bound(m, g, order, n + m, 10**1000)
            kernel = _chain_bound(n, order, order, n, 10**1000)
            lifts = image_order * m * order * 4 * (n + m)
            preimage = _chain_bound(n, order + image_order, order, n, 10**1000)
            work += image_chain + child + paired + kernel + lifts + preimage
            scans += 2 * image_order
        terminal_kinds.append("intransitive_small_order_orbit_images")
        scan_bounds.append(scans)
        per_branch.append(work)

    per_branch = tuple(per_branch)
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
        status = "certified_design_full_string_terminal_child_preflight"
        reason = "every branch is guaranteed to terminate either directly or through certified intransitive small-order orbit images, and the complete cover fits the finite budget"
    return DesignFullStringChildPreflight(
        status, root, n, len(frozen), orders, gate, per_branch, total, cap,
        root_lift, terminal_path, admitted, 0, 0, False, reason,
        tuple(terminal_kinds), tuple(orbit_image_orders), tuple(scan_bounds),
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
    permitted = sum(preflight.permutation_scan_upper_bounds[:len(frozen)])
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
