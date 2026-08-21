from __future__ import annotations

from dataclasses import dataclass, replace

from crx1_image_si_resource_bounds_v1 import (
    CRX1ImageSIRequest,
    _normalized_request,
    _require_nonnegative_int,
    _require_positive_int,
    _sat_add,
    _sat_mul,
    _sat_pow,
    johnson_relation_image_resource_request,
    recursive_coset_intersection_node_upper_bound,
)


_EXACT_INTERSECTION_STATUSES = frozenset(
    {"empty_intersection", "exact_intersection_coset"}
)


@dataclass(frozen=True)
class CRX1ImageSIExecution:
    """Execution counters returned by one admitted recursive intersection."""

    status: str
    search_nodes: int
    work_units: int


@dataclass(frozen=True)
class CRX1ImageSIResourceAdmission:
    """Immutable reserve-before-execute certificate for a complete CRX1 cover."""

    status: str
    root_degree: int
    parent_degree: int
    request_count: int
    polynomial_node_gate: int
    max_nodes_per_intersection: int
    max_total_nodes: int
    max_work: int
    requests: tuple[CRX1ImageSIRequest, ...]
    node_upper_bounds: tuple[int, ...]
    work_upper_bounds: tuple[int, ...]
    total_node_upper_bound: int
    total_work_upper_bound: int
    orders_certified: bool
    progress_certified: bool
    exact_intersection_path_certified: bool
    admitted: bool
    executed_request_count: int
    search_nodes_used: int
    work_units_used: int
    complete: bool
    reason: str




def crx1_image_si_resource_admission(
    requests,
    *,
    root_degree: int,
    parent_degree: int,
    image_si_poly_power: int,
    max_nodes_per_intersection: int,
    max_total_nodes: int,
    max_work: int,
) -> CRX1ImageSIResourceAdmission:
    """Reserve a complete exact image-SI cover before starting its first search.

    A node cap by itself is never an exactness certificate.  Admission requires
    certified subgroup orders, the theorem-derived worst-case node bound for each
    recursive intersection, strict/restricting recurrence progress (unless an
    independently certified whole-candidate terminal closes the same domain), and
    finite complete-cover node/work budgets.  Rejection starts no search and
    carries zero execution counters.
    """
    root = _require_positive_int("root_degree", root_degree)
    parent = _require_positive_int("parent_degree", parent_degree)
    power = _require_positive_int("image_si_poly_power", image_si_poly_power)
    per_cap = _require_positive_int("max_nodes_per_intersection", max_nodes_per_intersection)
    total_cap = _require_positive_int("max_total_nodes", max_total_nodes)
    work_cap = _require_positive_int("max_work", max_work)
    if parent > root:
        raise ValueError("parent_degree must not exceed root_degree")

    frozen = tuple(_normalized_request(request) for request in tuple(requests))
    polynomial_gate = min(per_cap, _sat_pow(root, power, per_cap + 1))
    node_stop = max(polynomial_gate, total_cap) + 1
    work_stop = work_cap + 1

    node_bounds = tuple(
        recursive_coset_intersection_node_upper_bound(
            request.image_degree,
            request.left_coset_order,
            request.right_coset_order,
            stop=node_stop,
        )
        for request in frozen
    )
    # A node bound can saturate at a smaller node cap than the work cap.
    # Recompute it with the work sentinel so rejected certificates never
    # understate their work envelope merely because node admission failed first.
    work_node_bounds = tuple(
        recursive_coset_intersection_node_upper_bound(
            request.image_degree,
            request.left_coset_order,
            request.right_coset_order,
            stop=work_stop,
        )
        for request in frozen
    )
    work_bounds = tuple(
        _sat_add(
            request.setup_work_upper_bound,
            _sat_mul(nodes, request.per_node_work_upper_bound, work_stop),
            work_stop,
        )
        for request, nodes in zip(frozen, work_node_bounds)
    )

    total_nodes = 0
    for nodes in node_bounds:
        total_nodes = _sat_add(total_nodes, nodes, total_cap + 1)
    total_work = 0
    for work in work_bounds:
        total_work = _sat_add(total_work, work, work_stop)

    orders_certified = bool(frozen) and all(
        request.left_order_certified and request.right_order_certified
        for request in frozen
    )
    progress_flags = []
    for request in frozen:
        if request.image_degree > parent:
            raise ValueError("image_degree must not exceed the parent degree")
        if request.strict_image_progress_certified and request.image_degree >= parent:
            raise ValueError("strict image progress certificate contradicts the image/parent degrees")
        progress_flags.append(
            request.whole_candidate_terminal_certified
            or (
                request.strict_image_progress_certified
                and request.image_degree < parent
                and request.restricting_preimage_certified
            )
        )
    progress_certified = bool(frozen) and all(progress_flags)
    per_item_fits = bool(frozen) and all(nodes <= polynomial_gate for nodes in node_bounds)
    cover_nodes_fit = bool(frozen) and total_nodes <= total_cap
    cover_work_fits = bool(frozen) and total_work <= work_cap
    exact_path = orders_certified and per_item_fits
    admitted = (
        bool(frozen)
        and exact_path
        and progress_certified
        and cover_nodes_fit
        and cover_work_fits
    )

    if not frozen:
        status = "crx1_image_si_empty_request_cover"
        reason = "no image intersection was supplied; an empty preflight cannot close a CRX1 leaf"
    elif not orders_certified:
        status = "crx1_image_si_order_certificate_unavailable"
        reason = "at least one input coset order is not certified; a node cap cannot replace the missing finite search-tree proof"
    elif not progress_certified:
        status = "crx1_image_si_nonrestricting_or_nonshrinking"
        reason = "at least one image is not certified as both strictly smaller and restricting, and no whole-candidate terminal closes the same-domain case"
    elif not per_item_fits:
        status = "crx1_image_si_per_intersection_node_bound_exceeded"
        reason = "a theorem-derived worst-case recursive intersection bound exceeds the polynomial/implementation node gate; no search was started"
    elif not cover_nodes_fit:
        status = "crx1_image_si_cover_node_bound_exceeded"
        reason = "the sum of the complete image-intersection cover exceeds the caller node budget before the first search"
    elif not cover_work_fits:
        status = "crx1_image_si_work_bound_exceeded"
        reason = "the complete setup plus theorem-derived recursive-search work envelope exceeds the caller budget before the first search"
    else:
        status = "certified_crx1_image_si_resource_admission"
        reason = "certified coset orders bound every recursive search below its node cap, strict/restricting progress is proved, and the complete cover fits the finite node/work budgets"

    return CRX1ImageSIResourceAdmission(
        status,
        root,
        parent,
        len(frozen),
        polynomial_gate,
        per_cap,
        total_cap,
        work_cap,
        frozen,
        node_bounds,
        work_bounds,
        total_nodes,
        total_work,
        orders_certified,
        progress_certified,
        exact_path,
        admitted,
        0,
        0,
        0,
        False,
        reason,
    )


def record_crx1_image_si_execution(
    admission: CRX1ImageSIResourceAdmission,
    executions,
    *,
    complete: bool,
) -> CRX1ImageSIResourceAdmission:
    """Audit actual recursive-intersection counters against an admitted reserve."""
    if not isinstance(admission, CRX1ImageSIResourceAdmission):
        raise TypeError("admission must be a CRX1ImageSIResourceAdmission")
    if not admission.admitted:
        raise ValueError("cannot record execution for a rejected CRX1 image-SI admission")
    frozen = tuple(executions)
    if any(not isinstance(item, CRX1ImageSIExecution) for item in frozen):
        raise TypeError("executions must contain CRX1ImageSIExecution values")
    if len(frozen) > admission.request_count:
        raise ValueError("executed intersection count exceeds the reserved cover")
    if complete and len(frozen) != admission.request_count:
        raise ValueError("complete execution omitted a reserved image intersection")

    nodes_used = 0
    work_used = 0
    for index, execution in enumerate(frozen):
        nodes = _require_positive_int("search_nodes", execution.search_nodes)
        work = _require_nonnegative_int("work_units", execution.work_units)
        if execution.status not in _EXACT_INTERSECTION_STATUSES:
            raise ValueError("an admitted image intersection did not return an exact recursive-intersection status")
        if nodes > admission.node_upper_bounds[index]:
            raise ValueError("actual recursive search nodes exceed the theorem-derived reservation")
        if work > admission.work_upper_bounds[index]:
            raise ValueError("actual image-SI work exceeds the reserved envelope")
        nodes_used += nodes
        work_used += work

    if nodes_used > admission.total_node_upper_bound:
        raise ValueError("aggregate recursive search nodes exceed the complete-cover reservation")
    if work_used > admission.total_work_upper_bound:
        raise ValueError("aggregate image-SI work exceeds the complete-cover reservation")

    return replace(
        admission,
        executed_request_count=len(frozen),
        search_nodes_used=nodes_used,
        work_units_used=work_used,
        complete=bool(complete),
    )


__all__ = [
    "CRX1ImageSIExecution",
    "CRX1ImageSIRequest",
    "CRX1ImageSIResourceAdmission",
    "crx1_image_si_resource_admission",
    "johnson_relation_image_resource_request",
    "record_crx1_image_si_execution",
    "recursive_coset_intersection_node_upper_bound",
]
