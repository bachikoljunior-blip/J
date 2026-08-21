from __future__ import annotations

from dataclasses import dataclass
from math import factorial

from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add, _sat_mul


@dataclass(frozen=True)
class NestedIntransitiveResourceEnvelope:
    status: str
    original_root_degree: int
    original_degree: int
    image_degree: int
    image_order_upper_bound: int
    small_order_gate: int
    recursion_node_upper_bound: int
    terminal_leaf_upper_bound: int
    permutation_scan_upper_bound: int
    work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    strict_degree_progress_certified: bool
    conditional_path_certified: bool
    admitted: bool
    reason: str


def _nested_bound(degree, order, generators, root_degree, gate, stop):
    """Bound every strict-smaller orbit recursion below one image.

    The caller supplies only an upper bound on the current image order.  On an
    orbit of size ``s`` the next image has order at most both the current order
    and ``s!``.  Replacing every possible nonempty orbit by ``degree`` copies of
    the worst strict size ``degree - 1`` therefore covers every intransitive
    orbit partition without knowing the post-child subgroup in advance.

    This is deliberately conditional: it bounds the path if every above-gate
    descendant is intransitive.  It does not certify that condition, and cannot
    be used to admit transitive imprimitive or primitive non-giant descendants.
    """
    degree = int(degree)
    order = min(int(order), factorial(degree))
    if order <= gate:
        work = _sat_mul(order, max(2, degree) ** 12 * (2 ** 24), stop)
        return 1, 1, 2 * order, work
    if degree <= 1:
        raise AssertionError("a degree-one permutation image cannot exceed the small-order gate")

    child_degree = degree - 1
    child_order = min(order, factorial(child_degree))
    child_nodes, child_leaves, child_scans, child_work = _nested_bound(
        child_degree, child_order, generators, root_degree, gate, stop
    )

    # One conservative S1 classification/orbit pass at this node.
    classify = _sat_mul(8 * degree * degree, max(generators, order), stop)

    # At most ``degree`` nonempty orbits exist.  Charge each as though it had
    # the largest strict degree and the largest possible image order.  The
    # paired/kernel/preimage terms mirror the executable S1 lift boundary.
    image_chain = _chain_bound(child_degree, generators, child_order, child_degree, stop)
    paired = _chain_bound(child_degree, generators, order, root_degree + child_degree, stop)
    kernel = _chain_bound(root_degree, order, order, root_degree, stop)
    lifts = _sat_mul(
        _sat_mul(child_order, child_degree, stop),
        _sat_mul(order, 4 * (root_degree + child_degree), stop),
        stop,
    )
    preimage = _chain_bound(root_degree, order + child_order, order, root_degree, stop)
    one_child = child_work
    for term in (image_chain, paired, kernel, lifts, preimage):
        one_child = _sat_add(one_child, term, stop)
    work = _sat_add(classify, _sat_mul(degree, one_child, stop), stop)
    nodes = 1 + degree * child_nodes
    leaves = degree * child_leaves
    scans = degree * child_scans
    return nodes, leaves, scans, work


def design_nested_intransitive_resource_envelope(
    *,
    original_root_degree: int,
    original_degree: int,
    image_degree: int,
    image_order_upper_bound: int,
    generator_upper_bound: int,
    small_order_gate: int,
    max_work: int,
) -> NestedIntransitiveResourceEnvelope:
    """Return a reserve-before-execute envelope for nested intransitive images.

    The result proves a finite resource bound for all strict-smaller orbit trees
    below the supplied image.  ``conditional_path_certified`` is intentionally
    false: a separate pre-execution certificate must show that every descendant
    above the small-order gate is intransitive before this envelope can admit a
    full Design branch cover.
    """
    root = int(original_root_degree)
    n = int(original_degree)
    degree = int(image_degree)
    order = int(image_order_upper_bound)
    generators = int(generator_upper_bound)
    gate = int(small_order_gate)
    cap = int(max_work)
    if min(root, n, degree, order, generators, gate, cap) <= 0:
        raise ValueError("invalid nested intransitive resource parameters")
    if degree > n:
        raise ValueError("nested image degree exceeds the current full-string degree")
    if order > factorial(degree):
        raise ValueError("image order upper bound exceeds the symmetric group order")

    root_lift = n <= root
    nodes, leaves, scans, work = _nested_bound(
        degree, order, generators, root, gate, cap + 1
    )
    within_cap = work <= cap
    if not root_lift:
        status = "design_nested_intransitive_original_root_lift_unavailable"
        reason = "the current full-string degree exceeds the original root"
    elif not within_cap:
        status = "design_nested_intransitive_work_cap_exceeded"
        reason = "the universal strict-smaller orbit envelope exceeds the finite budget"
    else:
        status = "certified_conditional_design_nested_intransitive_resource_envelope"
        reason = (
            "all strict-smaller intransitive orbit trees fit the finite budget; "
            "a separate pre-execution certificate of the intransitive-only path is still required"
        )
    return NestedIntransitiveResourceEnvelope(
        status=status,
        original_root_degree=root,
        original_degree=n,
        image_degree=degree,
        image_order_upper_bound=order,
        small_order_gate=gate,
        recursion_node_upper_bound=nodes,
        terminal_leaf_upper_bound=leaves,
        permutation_scan_upper_bound=scans,
        work_upper_bound=work,
        max_work=cap,
        root_lift_certified=root_lift,
        strict_degree_progress_certified=True,
        conditional_path_certified=False,
        admitted=False,
        reason=reason,
    )


__all__ = [
    "NestedIntransitiveResourceEnvelope",
    "design_nested_intransitive_resource_envelope",
]
