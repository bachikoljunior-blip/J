from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from math import factorial

from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add, _sat_mul


@dataclass(frozen=True)
class ImprimitiveQuotientKernelResourceEnvelope:
    status: str
    original_root_degree: int
    degree: int
    block_count: int
    block_size: int
    group_order: int
    source_generator_count: int
    quotient_order_upper_bound: int
    kernel_order_upper_bound: int
    small_order_gate: int
    child_terminal_kind: str
    child_state_image_upper_bound: int
    quotient_prepare_work_upper_bound: int
    quotient_enumeration_work_upper_bound: int
    quotient_lift_work_upper_bound: int
    child_work_per_fiber_upper_bound: int
    child_work_upper_bound: int
    reassembly_work_upper_bound: int
    work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    transitive_block_progress_certified: bool
    quotient_gate_certified: bool
    terminal_path_certified: bool
    admitted: bool
    permutation_scan_upper_bound: int
    executed_preparation_count: int
    executed_quotient_order: int
    executed_fiber_count: int
    permutation_candidates_checked: int
    complete: bool
    reason: str


def _normalize_blocks(blocks, degree: int):
    frozen = tuple(
        tuple(sorted({int(point) for point in block}))
        for block in blocks
    )
    frozen = tuple(sorted(frozen))
    if len(frozen) < 2 or any(len(block) < 2 for block in frozen):
        raise ValueError("a nontrivial full-domain block system is required")
    if tuple(sorted(point for block in frozen for point in block)) != tuple(range(degree)):
        raise ValueError("blocks must partition the full permutation domain")
    block_size = len(frozen[0])
    if any(len(block) != block_size for block in frozen):
        raise ValueError("transitive invariant blocks must have equal size")
    return frozen


def _multiset_permutation_count(values) -> int:
    values = tuple(values)
    try:
        counts = Counter(values)
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc
    total = factorial(len(values))
    for count in counts.values():
        total //= factorial(count)
    return total


def imprimitive_quotient_kernel_resource_envelope(
    group,
    blocks,
    target_values,
    *,
    original_root_degree: int,
    quotient_order_poly_power: int,
    max_quotient_image_order: int,
    candidate_group_order_poly_power: int,
    max_candidate_group_order: int,
    max_work: int,
) -> ImprimitiveQuotientKernelResourceEnvelope:
    """Reserve one complete transitive-imprimitive quotient/kernel execution.

    The unique canonical block system is already certified at this boundary.
    Before the first block-action image or Schreier operation, this envelope
    reserves a prepared quotient homomorphism, complete quotient enumeration,
    every quotient lift, one guaranteed exact child terminal per fiber, and the
    final disjoint-fiber right-coset reassembly.

    The quotient image has order at most ``min(|G|, q!)``.  Because the point
    action is transitive, its action on the ``q`` invariant blocks is transitive,
    so the exact kernel order is at most ``|G|/q``.  Above the existing small
    order gate, the child is terminalized by a completely reserved string-state
    orbit.  All arithmetic saturates only at the caller's arbitrary-precision
    ``cap+1``.
    """
    root = int(original_root_degree)
    n = int(group.degree)
    order = int(group.order)
    q_power = int(quotient_order_poly_power)
    candidate_power = int(candidate_group_order_poly_power)
    quotient_cap = int(max_quotient_image_order)
    candidate_cap = int(max_candidate_group_order)
    cap = int(max_work)
    if min(root, n, order, q_power, candidate_power, quotient_cap, candidate_cap, cap) <= 0:
        raise ValueError("invalid imprimitive quotient/kernel resource parameters")

    frozen_blocks = _normalize_blocks(blocks, n)
    q = len(frozen_blocks)
    block_size = len(frozen_blocks[0])
    if q * block_size != n or not (1 < q < n and 1 < block_size < n):
        raise ValueError("invalid nontrivial block dimensions")

    # Reading the already-built first Schreier orbit does not start a new block
    # action.  It mechanically checks the transitivity premise used below.
    transitive = bool(group.levels) and len(group.levels[0].orbit) == n
    if not transitive:
        raise ValueError("the quotient/kernel envelope requires a transitive group")
    if order % q:
        raise AssertionError("a transitive block action must make the block count divide |G|")

    generators = max(1, len(group.original_generators))
    quotient_upper = min(order, factorial(q))
    kernel_upper = max(1, order // q)
    quotient_gate = min(quotient_cap, root ** q_power)
    small_gate = min(candidate_cap, root ** candidate_power)
    root_lift = n <= root
    strict_progress = q < n and block_size < n
    quotient_gate_ok = quotient_upper <= quotient_gate
    stop = cap + 1

    # One prepared paired block-action homomorphism is shared by all lifts.
    block_actions = _sat_mul(8 * n, generators, stop)
    image_chain = _chain_bound(q, generators, quotient_upper, q, stop)
    paired_chain = _chain_bound(q, generators, order, n + q, stop)
    kernel_chain = _chain_bound(n, order, kernel_upper, n, stop)
    kernel_validation = _sat_mul(
        kernel_upper,
        16 * n * max(n, q),
        stop,
    )
    prepare = 0
    for part in (block_actions, image_chain, paired_chain, kernel_chain, kernel_validation):
        prepare = _sat_add(prepare, part, stop)

    quotient_steps = max(1, 2 * generators)
    enumeration = _sat_mul(
        quotient_upper,
        _sat_mul(quotient_steps, 8 * q, stop),
        stop,
    )

    # Every prepared lift performs at most q paired sifts, builds one domain
    # representative, verifies full-group membership and checks its block image.
    one_lift = 0
    for part in (
        32 * q * (n + q),
        _sat_mul(16 * n * n, order, stop),
        8 * n * q,
    ):
        one_lift = _sat_add(one_lift, part, stop)
    lifts = _sat_mul(quotient_upper, one_lift, stop)

    target = tuple(target_values)
    if len(target) != n:
        raise ValueError("target string/block-action degree mismatch")
    multiset = _multiset_permutation_count(target)
    state_upper = min(kernel_upper, multiset)
    if kernel_upper <= small_gate:
        terminal_kind = "small_order"
        child_per = _sat_mul(
            kernel_upper,
            max(2, n) ** 12 * (2 ** 24),
            stop,
        )
        scans_per_fiber = 2 * kernel_upper
    else:
        terminal_kind = "state_orbit"
        kernel_generators = max(1, kernel_upper)
        state_action = _sat_mul(
            state_upper,
            _sat_mul(kernel_generators, n, stop),
            stop,
        )
        state_chain = _chain_bound(
            n,
            _sat_mul(state_upper, kernel_generators, stop),
            kernel_upper,
            n,
            stop,
        )
        child_per = _sat_add(state_action, state_chain, stop)
        scans_per_fiber = state_upper
    child_total = _sat_mul(quotient_upper, child_per, stop)
    scan_upper = _sat_mul(quotient_upper, scans_per_fiber,stop)

    generator_inputs = _sat_mul(
        quotient_upper,
        kernel_upper + 1,
        stop,
    )
    union_chain = _chain_bound(n, max(1, generator_inputs), order, n, stop)
    union_audit = _sat_mul(
        generator_inputs,
        _sat_mul(16 * n * n, order, stop),
        stop,
    )
    reassembly = _sat_add(union_chain, union_audit, stop)

    total = 0
    for part in (prepare, enumeration, lifts, child_total, reassembly):
        total = _sat_add(total, part, stop)

    terminal_path = terminal_kind in {"small_order", "state_orbit"}
    admitted = (
        root_lift
        and strict_progress
        and quotient_gate_ok
        and terminal_path
        and total <= cap
    )
    if not root_lift:
        status = "imprimitive_quotient_kernel_original_root_lift_unavailable"
        reason = "the current imprimitive domain exceeds the original root"
    elif not strict_progress:
        status = "imprimitive_quotient_kernel_block_progress_unavailable"
        reason = "the supplied block system does not give strict quotient and kernel-domain progress"
    elif not quotient_gate_ok:
        status = "imprimitive_quotient_kernel_quotient_gate_unavailable"
        reason = "the universal quotient-image order bound exceeds the configured polynomial/runtime gate"
    elif total > cap:
        status = "imprimitive_quotient_kernel_work_cap_exceeded"
        reason = "the complete quotient/kernel, exact-fiber terminal and reassembly reservation exceeds the finite budget before the first block action"
    else:
        status = "certified_imprimitive_quotient_kernel_resource_envelope"
        reason = (
            "one prepared block-action homomorphism, the complete quotient image, "
            "all exact fiber terminals and final coset reassembly fit the finite "
            "original-root budget before the first block action"
        )

    return ImprimitiveQuotientKernelResourceEnvelope(
        status=status,
        original_root_degree=root,
        degree=n,
        block_count=q,
        block_size=block_size,
        group_order=order,
        source_generator_count=generators,
        quotient_order_upper_bound=quotient_upper,
        kernel_order_upper_bound=kernel_upper,
        small_order_gate=small_gate,
        child_terminal_kind=terminal_kind,
        child_state_image_upper_bound=state_upper,
        quotient_prepare_work_upper_bound=prepare,
        quotient_enumeration_work_upper_bound=enumeration,
        quotient_lift_work_upper_bound=lifts,
        child_work_per_fiber_upper_bound=child_per,
        child_work_upper_bound=child_total,
        reassembly_work_upper_bound=reassembly,
        work_upper_bound=total,
        max_work=cap,
        root_lift_certified=root_lift,
        transitive_block_progress_certified=strict_progress,
        quotient_gate_certified=quotient_gate_ok,
        terminal_path_certified=terminal_path,
        admitted=admitted,
        permutation_scan_upper_bound=scan_upper,
        executed_preparation_count=0,
        executed_quotient_order=0,
        executed_fiber_count=0,
        permutation_candidates_checked=0,
        complete=False,
        reason=reason,
    )


def record_imprimitive_quotient_kernel_execution(
    envelope: ImprimitiveQuotientKernelResourceEnvelope,
    children,
    *,
    prepared_homomorphism_count: int,
    quotient_order: int,
    complete: bool,
) -> ImprimitiveQuotientKernelResourceEnvelope:
    if not envelope.admitted:
        raise ValueError("cannot record execution against a rejected imprimitive envelope")
    preparations = int(prepared_homomorphism_count)
    q_order = int(quotient_order)
    if preparations != 1:
        raise ValueError("an admitted execution must prepare the block homomorphism exactly once")
    if q_order < 1 or q_order > envelope.quotient_order_upper_bound:
        raise ValueError("executed quotient order exceeds the reserved universal bound")

    frozen = tuple(children)
    if len(frozen) > q_order:
        raise ValueError("executed fiber count exceeds the exact quotient order")
    if complete and len(frozen) != q_order:
        raise ValueError("complete quotient execution omitted a reserved fiber")
    if complete and any(not child.exact for child in frozen):
        raise ValueError("a complete reserved quotient execution contains a nonexact child")

    checked = sum(int(child.permutation_candidates_checked) for child in frozen)
    if envelope.child_terminal_kind == "small_order":
        scans_per_fiber = 2 * envelope.kernel_order_upper_bound
    else:
        scans_per_fiber = envelope.child_state_image_upper_bound
    permitted = q_order * scans_per_fiber
    if checked > permitted or checked > envelope.permutation_scan_upper_bound:
        raise ValueError("executed fiber scans exceed the reserved exact-terminal bound")

    return replace(
        envelope,
        executed_preparation_count=preparations,
        executed_quotient_order=q_order,
        executed_fiber_count=len(frozen),
        permutation_candidates_checked=checked,
        complete=bool(complete),
    )


__all__ = [
    "ImprimitiveQuotientKernelResourceEnvelope",
    "imprimitive_quotient_kernel_resource_envelope",
    "record_imprimitive_quotient_kernel_execution",
]
