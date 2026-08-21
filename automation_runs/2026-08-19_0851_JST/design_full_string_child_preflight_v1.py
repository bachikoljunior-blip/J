from __future__ import annotations

from dataclasses import dataclass, replace

from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add
from orbit_factored_string_coset_intersection_v1 import _group_orbits, _image_chain
from proof_carrying_state_orbit_candidate_v1 import state_orbit_candidate_envelope


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
    state_orbit_work_upper_bounds: tuple[int, ...] = ()
    state_orbit_image_upper_bounds: tuple[int, ...] = ()


def design_full_string_child_preflight(
    branches,
    *,
    original_root_degree: int,
    original_degree: int,
    group_order_poly_power: int,
    max_group_order: int,
    max_work: int,
    target_values=None,
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
    stop = cap + 1
    scale = max(2, n) ** 12 * (2 ** 24)

    # Production Design callers provide the target string.  This lets us avoid
    # predicting an intransitive/imprimitive/primitive path altogether: reserve
    # the complete state orbit for every branch that misses the small-order
    # terminal, sum the whole cover with caller-derived cap+1 saturation, and
    # admit only after that sum is known.  Computing these envelopes never starts
    # the state search.  Legacy callers without target_values retain the earlier
    # structural preflight below.
    if target_values is not None:
        target = tuple(target_values)
        if len(target) != n:
            raise ValueError("target string/Design child degree mismatch")
        legacy = design_full_string_child_preflight(
            frozen,
            original_root_degree=root,
            original_degree=n,
            group_order_poly_power=power,
            max_group_order=implementation_cap,
            max_work=cap,
        )
        # Do not replace an already certified direct/intransitive path merely
        # because the state orbit is cheaper.  Besides preserving replay-stable
        # accounting, this ensures the new terminal only removes branches whose
        # structural path was genuinely unresolved.  A certified legacy path
        # that misses the caller budget remains rejected rather than silently
        # changing algorithms.
        if all(order <= gate for order in orders) or legacy.terminal_path_certified:
            return legacy
        envelopes = tuple(
            state_orbit_candidate_envelope(branch.coset, target, max_work=cap)
            for branch in frozen
        )
        state_work = tuple(int(envelope.work_upper_bound) for envelope in envelopes)
        state_images = tuple(int(envelope.state_image_upper_bound) for envelope in envelopes)
        kinds = tuple(
            "small_order" if order <= gate else (
                "state_orbit" if envelope.admitted else "unresolved_state_orbit"
            )
            for order, envelope in zip(orders, envelopes)
        )
        per_branch = tuple(
            order * scale if kind == "small_order" else work
            for order, kind, work in zip(orders, kinds, state_work)
        )
        total = 0
        for work in per_branch:
            total = _sat_add(total, int(work), stop)
        terminal_path = all(kind in {"small_order", "state_orbit"} for kind in kinds)
        admitted = root_lift and terminal_path and total <= cap
        scans = tuple(
            2 * order if kind == "small_order" else (
                image_bound if kind == "state_orbit" else 0
            )
            for order, kind, image_bound in zip(orders, kinds, state_images)
        )
        if not root_lift:
            status = "design_full_string_child_original_root_lift_unavailable"
            reason = "the full-string child degree exceeds the original root"
        elif not terminal_path:
            status = "design_full_string_state_orbit_cover_work_cap_exceeded"
            reason = "at least one complete branch state orbit exceeds the finite budget; no branch or structural child was started"
        elif total > cap:
            status = "design_full_string_state_orbit_cover_work_cap_exceeded"
            reason = "the sum of all exact branch terminal reservations exceeds the finite budget before the first branch"
        else:
            status = "certified_design_full_string_state_orbit_cover_preflight"
            reason = "every surviving Design branch has an exact small-order or complete state-orbit terminal and the entire cover was reserved before the first branch"
        return DesignFullStringChildPreflight(
            status, root, n, len(frozen), orders, gate, per_branch, total, cap,
            root_lift, terminal_path, admitted, 0, 0, False, reason,
            kinds, tuple(() for _ in orders), scans, state_work, state_images,
        )
    # Reserve the complete-cover structural audit before constructing even one
    # orbit image.  At most n canonical orbits exist, and each image chain is
    # bounded by the full branch degree/order.  The factor two separately pays
    # for this immutable preflight audit and the later S1 classification pass.
    audit_reservations = []
    for branch, order in zip(frozen, orders):
        if order <= gate:
            audit_reservations.append(order * scale)
            continue
        group = branch.coset.subgroup
        g = max(1, len(group.original_generators))
        orbit_work = 8 * n * n * max(g, order)
        all_image_chains = n * _chain_bound(n, g, order, n, stop)
        audit_reservations.append(2 * (orbit_work + all_image_chains))
    audit_total = sum(audit_reservations)
    has_structural = any(order > gate for order in orders)
    if not root_lift or audit_total > cap:
        status = (
            "design_full_string_child_original_root_lift_unavailable"
            if not root_lift else (
                "design_full_string_child_audit_work_cap_exceeded"
                if has_structural else "design_full_string_child_work_cap_exceeded"
            )
        )
        reason = (
            "the full-string child degree exceeds the original root"
            if not root_lift else (
                "the complete-cover orbit/image audit reservation exceeds the finite budget before any structural audit or child"
                if has_structural else
                "the complete small-order child cover exceeds the finite budget before the first child"
            )
        )
        return DesignFullStringChildPreflight(
            status, root, n, len(frozen), orders, gate,
            tuple(audit_reservations), audit_total, cap,
            root_lift, False, False, 0, 0, False, reason,
            tuple("small_order" if order <= gate else "unexamined_structural" for order in orders),
            tuple(() for _ in orders), tuple(2 * order if order <= gate else 0 for order in orders),
        )

    for branch, order, audit_reservation in zip(frozen, orders, audit_reservations):
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
        work = audit_reservation
        scans = 0
        for orbit, image_order in zip(orbits, image_orders):
            m = len(orbit)
            child = image_order * (max(2, m) ** 12) * (2 ** 24)
            paired = _chain_bound(m, g, order, n + m, stop)
            kernel = _chain_bound(n, order, order, n, stop)
            lifts = image_order * m * order * 4 * (n + m)
            preimage = _chain_bound(n, order + image_order, order, n, stop)
            work += child + paired + kernel + lifts + preimage
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
