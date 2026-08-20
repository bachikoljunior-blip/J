from __future__ import annotations

from dataclasses import dataclass

from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add, _sat_mul


@dataclass(frozen=True)
class AffectedSegmentReassemblyResourceEnvelope:
    status: str
    domain_degree: int
    quotient_degree: int
    quotient_leaf_upper_bound: int
    quotient_node_upper_bound: int
    internal_node_upper_bound: int
    generator_input_upper_bound: int
    containment_sift_upper_bound: int
    work_upper_bound: int
    max_work: int
    admitted: bool
    reason: str


@dataclass(frozen=True)
class AffectedSegmentReassemblyExecutionCharge:
    internal_nodes: int
    generator_inputs: int
    containment_sifts: int
    envelope_verified: bool


def affected_segment_reassembly_resource_envelope(
    group,
    quotient_degree: int,
    quotient_leaf_upper_bound: int,
    quotient_node_upper_bound: int,
    max_work: int,
) -> AffectedSegmentReassemblyResourceEnvelope:
    """Preflight every full-domain parent-coset rebuild and containment sift."""
    cap = int(max_work)
    if cap < 0:
        raise ValueError("remaining reassembly work cap must be nonnegative")
    n = int(group.degree)
    t = int(quotient_degree)
    order = max(1, int(group.order))
    leaves = int(quotient_leaf_upper_bound)
    nodes = int(quotient_node_upper_bound)
    stop = cap + 1

    internal = max(0, nodes - leaves)
    per_internal_inputs = _sat_mul(t, order + 1, stop)
    generator_inputs = _sat_mul(internal, per_internal_inputs, stop)
    containment_sifts = generator_inputs
    per_chain = _chain_bound(n, per_internal_inputs, order, n, stop)
    per_sifts = _sat_mul(8 * n * n, per_internal_inputs, stop)
    work = _sat_mul(internal, _sat_add(per_chain, per_sifts, stop), stop)
    admitted = work <= cap
    return AffectedSegmentReassemblyResourceEnvelope(
        "certified_affected_segment_reassembly_work_bound" if admitted
        else "affected_segment_reassembly_work_cap_exceeded",
        n, t, leaves, nodes, internal, generator_inputs,
        containment_sifts, work, cap, admitted,
        (
            "a conservative finite bound covers every parent subgroup chain and child-containment sift"
            if admitted else
            "the complete parent-coset reassembly bound exceeds the cap; quotient execution was not started"
        ),
    )


__all__ = [
    "AffectedSegmentReassemblyResourceEnvelope",
    "AffectedSegmentReassemblyExecutionCharge",
    "affected_segment_reassembly_resource_envelope",
]
