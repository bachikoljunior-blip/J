from __future__ import annotations

from dataclasses import dataclass


def _sat_add(left: int, right: int, stop: int) -> int:
    if left < 0 or right < 0 or stop <= 0:
        raise ValueError("saturating arithmetic requires non-negative operands and positive stop")
    total = left + right
    return stop if total >= stop else total


def _sat_mul(left: int, right: int, stop: int) -> int:
    if left < 0 or right < 0 or stop <= 0:
        raise ValueError("saturating arithmetic requires non-negative operands and positive stop")
    if left == 0 or right == 0:
        return 0
    if left >= stop or right >= stop or left > (stop - 1) // right:
        return stop
    product = left * right
    return stop if product >= stop else product


@dataclass(frozen=True, slots=True)
class ImplicitRelationImageResourceEnvelope:
    status: str
    original_root_degree: int
    domain_degree: int
    auxiliary_degree: int
    generator_count: int
    domain_order_upper_bound: int
    image_order_upper_bound: int
    image_order_gate: int
    action_work_upper_bound: int
    domain_schreier_work_upper_bound: int
    image_schreier_work_upper_bound: int
    value_coset_intersection_work_upper_bound: int
    paired_preimage_work_upper_bound: int
    verification_work_upper_bound: int
    work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    order_bounds_compatible: bool
    image_gate_certified: bool
    admitted: bool
    complete: bool
    reason: str


def _chain_bound(
    degree: int,
    generator_count: int,
    order_upper_bound: int,
    action_degree: int,
    stop: int,
) -> int:
    """Conservative raw Schreier/sift work envelope."""
    return _sat_mul(
        order_upper_bound,
        _sat_mul(
            max(1, generator_count),
            32 * max(1, degree) * max(1, action_degree),
            stop,
        ),
        stop,
    )


def implicit_relation_image_resource_envelope(
    *,
    original_root_degree: int,
    domain_degree: int,
    auxiliary_degree: int,
    generator_count: int,
    domain_order_upper_bound: int,
    image_order_upper_bound: int,
    image_order_poly_power: int,
    max_image_order: int,
    max_work: int,
) -> ImplicitRelationImageResourceEnvelope:
    """Reserve one complete bounded implicit relation-image attempt.

    The envelope is intentionally independent of rev257's unmerged implementation
    module.  It can be evaluated before the exact image group exists and reserves:

    * construction/verification of the induced auxiliary generators;
    * implicit domain and image Schreier chains;
    * complete intersection with the value-preserving auxiliary right coset below
      a caller-derived image-order gate;
    * paired original-domain preimage reconstruction; and
    * final source/target transport and subgroup-containment verification.

    Admission is a finite resource claim only.  ``complete`` remains false because
    exact image-coset intersection and preimage integration are separate execution
    obligations.
    """
    root = int(original_root_degree)
    n = int(domain_degree)
    aux = int(auxiliary_degree)
    generators = int(generator_count)
    domain_order = int(domain_order_upper_bound)
    image_order = int(image_order_upper_bound)
    power = int(image_order_poly_power)
    implementation_cap = int(max_image_order)
    cap = int(max_work)

    if min(
        root,
        n,
        aux,
        generators,
        domain_order,
        image_order,
        power,
        implementation_cap,
        cap,
    ) <= 0:
        raise ValueError("all resource-envelope parameters must be positive")
    if image_order > domain_order:
        raise ValueError("image-order upper bound cannot exceed domain-order upper bound")

    stop = cap + 1
    root_lift = n <= root and aux <= root * root
    order_bounds_compatible = image_order <= domain_order
    image_gate = min(implementation_cap, root ** power)
    image_gate_ok = image_order <= image_gate

    action = _sat_mul(generators, 16 * (n + aux), stop)
    domain_chain = _chain_bound(n, generators, domain_order, n, stop)
    image_chain = _chain_bound(aux, generators, image_order, aux, stop)

    intersection_per_image = _sat_add(
        8 * aux,
        _sat_mul(32 * aux * aux, max(1, image_order), stop),
        stop,
    )
    intersection = _sat_mul(image_order, intersection_per_image, stop)

    # image_order is only an upper bound, so dividing the domain-order upper bound
    # would under-reserve the kernel.  Reserve the whole domain order instead.
    kernel_upper = domain_order
    paired_inputs = _sat_add(generators, kernel_upper, stop)
    paired_chain = _chain_bound(
        n + aux,
        paired_inputs,
        domain_order,
        n + aux,
        stop,
    )
    lift_sifts = _sat_mul(
        image_order,
        _sat_mul(32 * n * (n + aux), max(1, domain_order), stop),
        stop,
    )
    paired_preimage = _sat_add(paired_chain, lift_sifts, stop)

    verification_inputs = _sat_add(kernel_upper, image_order, stop)
    verification = _sat_mul(
        verification_inputs,
        _sat_mul(16 * n * n, max(1, domain_order), stop),
        stop,
    )

    total = 0
    for part in (
        action,
        domain_chain,
        image_chain,
        intersection,
        paired_preimage,
        verification,
    ):
        total = _sat_add(total, part, stop)

    admitted = root_lift and image_gate_ok and total <= cap
    if not root_lift:
        status = "implicit_relation_image_original_root_lift_unavailable"
        reason = "domain or auxiliary degree exceeds the original-root lift gate"
    elif not image_gate_ok:
        status = "implicit_relation_image_order_gate_exceeded"
        reason = "image-order bound exceeds the caller-derived original-root polynomial gate"
    elif total > cap:
        status = "implicit_relation_image_work_cap_exceeded"
        reason = "the complete bounded image intersection/preimage attempt exceeds max_work"
    else:
        status = "certified_implicit_relation_image_work_bound"
        reason = "the complete bounded image intersection, preimage, and verification fit one original-root budget"

    return ImplicitRelationImageResourceEnvelope(
        status=status,
        original_root_degree=root,
        domain_degree=n,
        auxiliary_degree=aux,
        generator_count=generators,
        domain_order_upper_bound=domain_order,
        image_order_upper_bound=image_order,
        image_order_gate=image_gate,
        action_work_upper_bound=action,
        domain_schreier_work_upper_bound=domain_chain,
        image_schreier_work_upper_bound=image_chain,
        value_coset_intersection_work_upper_bound=intersection,
        paired_preimage_work_upper_bound=paired_preimage,
        verification_work_upper_bound=verification,
        work_upper_bound=total,
        max_work=cap,
        root_lift_certified=root_lift,
        order_bounds_compatible=order_bounds_compatible,
        image_gate_certified=image_gate_ok,
        admitted=admitted,
        complete=False,
        reason=reason,
    )


__all__ = [
    "ImplicitRelationImageResourceEnvelope",
    "implicit_relation_image_resource_envelope",
]
