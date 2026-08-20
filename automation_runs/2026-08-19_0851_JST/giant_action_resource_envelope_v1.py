from __future__ import annotations

from dataclasses import dataclass

from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add, _sat_mul


@dataclass(frozen=True)
class GiantActionResourceEnvelope:
    status: str
    domain_degree: int
    quotient_degree: int
    source_generator_count: int
    source_group_order: int
    work_upper_bound: int
    max_work: int
    admitted: bool
    reason: str


def _point_stabilizer_step_bound(n: int, order: int, stop: int) -> int:
    # orbit_transversal plus all Schreier generators, followed by the raw chain.
    pairs = _sat_mul(n, order, stop)
    primitive = _sat_mul(12 * n, pairs, stop)
    chain = _chain_bound(n, order, order, n, stop)
    return _sat_add(primitive, chain, stop)


def giant_action_resource_envelope(group, quotient_degree: int, max_work: int):
    """Fail-before-execution bound for one complete giant-action audit.

    Covers the quotient image chain, paired kernel recursion and kernel chain,
    domain-orbit discovery, every orbit-representative point stabilizer and its
    quotient image, the theorem-side pointwise unaffected stabilizer and image,
    and all kernel-orbit checks.  Bounds deliberately use the source group order
    for every intermediate generator family, so they remain valid without
    executing any structural primitive first.
    """
    cap = int(max_work)
    if cap <= 0:
        raise ValueError("max_giant_action_schreier_work must be positive")
    n = int(group.degree)
    k = int(quotient_degree)
    order = max(1, int(group.order))
    generators = max(1, len(group.original_generators))
    stop = cap + 1

    image = _chain_bound(k, generators, order, k, stop)
    paired = _chain_bound(k, generators, order, n + k, stop)
    kernel = _chain_bound(n, order, order, n, stop)
    orbit_work = _sat_mul(2 * n, _sat_mul(n, order, stop), stop)
    one_stabilizer = _point_stabilizer_step_bound(n, order, stop)
    per_orbit = _sat_mul(n, _sat_add(one_stabilizer, _chain_bound(k, order, order, k, stop), stop), stop)
    theorem_stabilizer = _sat_mul(n, one_stabilizer, stop)
    theorem_image = _chain_bound(k, order, order, k, stop)

    total = 0
    for part in (image, paired, kernel, orbit_work, per_orbit, theorem_stabilizer, theorem_image):
        total = _sat_add(total, part, stop)
    admitted = total <= cap
    return GiantActionResourceEnvelope(
        "certified_giant_action_work_bound" if admitted else "giant_action_work_cap_exceeded",
        n, k, generators, order, total, cap, admitted,
        (
            "a conservative finite bound covers every raw Schreier/orbit primitive in one giant-action audit"
            if admitted else
            "the complete giant-action audit bound exceeds the remaining cap; no structural audit was executed"
        ),
    )


__all__ = ["GiantActionResourceEnvelope", "giant_action_resource_envelope"]
