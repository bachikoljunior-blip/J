from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreimageSchreierResourceEnvelope:
    status: str
    domain_degree: int
    quotient_degree: int
    source_generator_count: int
    alternating_generator_count: int
    work_upper_bound: int
    max_work: int
    admitted: bool
    reason: str


def _sat_add(a: int, b: int, stop: int) -> int:
    return min(stop, a + b)


def _sat_mul(a: int, b: int, stop: int) -> int:
    if not a or not b:
        return 0
    return stop if a > stop // b else min(stop, a * b)


def _chain_bound(degree, generators, group_order, coordinate_cost, stop):
    """Bound generator/orbit pair work in the repository's raw Schreier chain.

    At every base level the transversal has at most ``degree`` entries.  Both
    orbit construction and Schreier generation visit at most one
    (transversal-entry, current-generator) pair each.  Deduplication leaves no
    more than ``group_order`` distinct permutations and the next raw family has
    at most ``degree * current`` elements.  ``8 * coordinate_cost`` covers the
    fixed number of permutation scans/compositions per visited pair.
    """
    d = max(1, int(degree))
    order = max(1, int(group_order))
    current = min(order, max(1, int(generators)))
    work = 0
    for _ in range(d):
        pairs = _sat_mul(2 * d, current, stop)
        work = _sat_add(work, _sat_mul(8 * int(coordinate_cost), pairs, stop), stop)
        current = min(order, _sat_mul(d, current, stop))
    return work


def preimage_schreier_resource_envelope(
    group,
    quotient_degree: int,
    alternating_generator_count: int,
    max_work: int,
) -> PreimageSchreierResourceEnvelope:
    """Fail-before-execution bound for the complete A(T)-preimage phase.

    The bound covers the quotient image chain, paired quotient chain, exact
    kernel chain, every prepared lift sift, and the final generated preimage
    chain.  It is deliberately conservative: exceeding the cap returns unknown
    before any of those chains are constructed.
    """
    cap = int(max_work)
    if cap <= 0:
        raise ValueError("max_preimage_schreier_work must be positive")
    n = int(group.degree)
    k = int(quotient_degree)
    a = int(alternating_generator_count)
    g = max(1, len(group.original_generators))
    order = max(1, int(group.order))
    stop = cap + 1

    image = _chain_bound(k, g, order, k, stop)
    paired = _chain_bound(k, g, order, n + k, stop)
    # The paired residual family is deduplicated inside the source group.
    kernel = _chain_bound(n, order, order, n, stop)
    lift_sifts = _sat_mul(a, _sat_mul(k, _sat_mul(order, 4 * (n + k), stop), stop), stop)
    preimage = _chain_bound(n, order + max(1, a), order, n, stop)
    total = 0
    for part in (image, paired, kernel, lift_sifts, preimage):
        total = _sat_add(total, part, stop)
    admitted = total <= cap
    return PreimageSchreierResourceEnvelope(
        "certified_preimage_schreier_work_bound" if admitted else "preimage_schreier_work_cap_exceeded",
        n,
        k,
        g,
        a,
        total,
        cap,
        admitted,
        (
            "a conservative finite bound covers every raw Schreier/preimage primitive before execution"
            if admitted
            else "the conservative complete preimage-phase bound exceeds the cap; no preimage chain was executed"
        ),
    )


__all__ = ["PreimageSchreierResourceEnvelope", "preimage_schreier_resource_envelope"]
