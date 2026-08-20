from __future__ import annotations

from dataclasses import dataclass

from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add, _sat_mul


@dataclass(frozen=True)
class AffectedSegmentQuotientResourceEnvelope:
    status: str
    domain_degree: int
    quotient_degree: int
    quotient_order: int
    quotient_leaf_upper_bound: int
    quotient_node_upper_bound: int
    kernel_child_upper_bound: int
    child_search_node_upper_bound: int
    work_upper_bound: int
    max_work: int
    admitted: bool
    reason: str


def affected_segment_quotient_resource_envelope(
    group,
    quotient_degree: int,
    quotient_order: int,
    *,
    max_quotient_leaves: int,
    max_child_nodes: int,
    max_work: int,
) -> AffectedSegmentQuotientResourceEnvelope:
    """Preflight the quotient recursion through kernel-orbit child SI.

    The bound covers quotient point-image nodes, one shared paired block-action
    preparation, every singleton lift, kernel-orbit discovery, every active-orbit
    image/point-image child, and every paired orbit-action preimage.  Parent coset
    reassembly is intentionally the next problem-tree child and is not claimed.
    """
    cap = int(max_work)
    if cap < 0:
        raise ValueError("remaining affected-segment work cap must be nonnegative")
    n = int(group.degree)
    t = int(quotient_degree)
    order = max(1, int(group.order))
    qorder = max(1, int(quotient_order))
    leaves = qorder
    # Multiplicity evidence is exact and reusable by later envelopes.  Only the
    # work sum saturates; saturating counts at this cap could understate a later
    # independently capped phase.
    nodes = 1 + t * leaves
    kernel_children = leaves * n
    # The fail-closed counter observes limit+1 on the rejecting tick.
    child_nodes = kernel_children * (int(max_child_nodes) + 1)
    stop = cap + 1

    # One shared block-action image/paired-kernel preparation.
    prepare = 0
    for part in (
        _chain_bound(t, max(1, len(group.original_generators)), order, t, stop),
        _chain_bound(t, max(1, len(group.original_generators)), order, n + t, stop),
        _chain_bound(n, order, order, n, stop),
    ):
        prepare = _sat_add(prepare, part, stop)

    quotient_node = _sat_add(
        _sat_mul(24 * t, _sat_mul(t, order, stop), stop),
        _chain_bound(t, order, order, t, stop),
        stop,
    )
    quotient_work = _sat_mul(nodes, quotient_node, stop)
    lifts = _sat_mul(leaves, _sat_mul(4 * t, _sat_mul(order, n + t, stop), stop), stop)
    orbit_discovery = _sat_mul(leaves, _sat_mul(n, _sat_mul(n, order, stop), stop), stop)

    per_child_chain = _chain_bound(n, order, order, n, stop)
    per_search_node = _sat_add(
        _sat_mul(96 * n, _sat_mul(n, order, stop), stop),
        _sat_mul(6, per_child_chain, stop),
        stop,
    )
    child_search = _sat_mul(child_nodes, per_search_node, stop)
    # Orbit image + paired kernel + kernel/preimage chains and all child-generator lifts.
    per_child_preimage = _sat_mul(5, per_child_chain, stop)
    child_preimages = _sat_mul(kernel_children, per_child_preimage, stop)

    total = 0
    for part in (prepare, quotient_work, lifts, orbit_discovery, child_search, child_preimages):
        total = _sat_add(total, part, stop)

    leaves_admitted = leaves <= int(max_quotient_leaves)
    admitted = leaves_admitted and total <= cap
    status = (
        "quotient_leaf_cap_exceeded_before_execution" if not leaves_admitted
        else "affected_segment_quotient_work_cap_exceeded" if not admitted
        else "certified_affected_segment_quotient_work_bound"
    )
    return AffectedSegmentQuotientResourceEnvelope(
        status, n, t, qorder, leaves, nodes, kernel_children, child_nodes,
        total, cap, admitted,
        (
            "the exact quotient order exceeds the leaf cap before recursion"
            if not leaves_admitted else
            "the conservative quotient/kernel-child primitive bound exceeds the remaining cap; recursion was not started"
            if not admitted else
            "a conservative finite bound covers quotient recursion through every kernel-orbit child preimage"
        ),
    )


__all__ = [
    "AffectedSegmentQuotientResourceEnvelope",
    "affected_segment_quotient_resource_envelope",
]
