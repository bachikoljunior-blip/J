from __future__ import annotations

from dataclasses import dataclass
from math import comb, factorial

from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add, _sat_mul


@dataclass(frozen=True)
class NestedPrimitiveJohnsonResourceEnvelope:
    status: str
    original_root_degree: int
    original_degree: int
    image_degree: int
    parent_order_upper_bound: int
    image_order_upper_bound: int
    generator_upper_bound: int
    johnson_parameter_candidates: tuple[tuple[int, int], ...]
    max_ground_size: int
    max_subset_size: int
    pair_count: int
    recognition_comparison_upper_bound: int
    recognition_node_upper_bound: int
    partition_state_upper_bound: int
    partition_action_upper_bound: int
    recognition_work_upper_bound: int
    relation_profile_work_upper_bound: int
    partition_transport_work_upper_bound: int
    schreier_work_upper_bound: int
    original_root_lift_work_upper_bound: int
    work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    johnson_parameter_cover_certified: bool
    strict_ground_progress_certified: bool
    johnson_action_order_certified: bool
    resource_admitted: bool
    exact_path_certified: bool
    reason: str

    @property
    def admitted(self) -> bool:
        """Full-branch admission remains false until a path certificate exists."""
        return self.resource_admitted and self.exact_path_certified


def _johnson_parameter_candidates(vertex_count: int) -> tuple[tuple[int, int], ...]:
    m = int(vertex_count)
    return tuple(
        (v, k)
        for v in range(4, m + 1)
        for k in range(2, v // 2 + 1)
        if comb(v, k) == m
    )


def design_nested_primitive_johnson_resource_envelope(
    *,
    original_root_degree: int,
    original_degree: int,
    image_degree: int,
    parent_order_upper_bound: int,
    image_order_upper_bound: int,
    generator_upper_bound: int,
    max_recognition_nodes: int,
    max_robust_orbital_degree: int,
    partition_state_poly_power: int,
    max_partition_states: int,
    max_work: int,
) -> NestedPrimitiveJohnsonResourceEnvelope:
    """Reserve the nested primitive non-giant Johnson/profile path before H exists.

    The caller supplies only upper bounds available before an earlier orbit child
    has fixed the later current subgroup.  The envelope covers the exact Johnson
    parameter scan, canonical orbital-size recognition, the bounded exact-orbital
    fallback, generator decode/re-induction, complement-safe star/profile tables,
    the complete bounded signed partition-orbit attempt with its original-domain
    Schreier chains, and the paired image/kernel/preimage lift back to the current
    full-string domain.

    Admission is a resource statement only.  It does not claim that the unknown
    post-child subgroup will be primitive, Johnson, profile-determined, or exact.
    Every such semantic outcome remains checked by the existing S1/U2 code.
    """
    root = int(original_root_degree)
    n = int(original_degree)
    m = int(image_degree)
    parent_order = int(parent_order_upper_bound)
    image_order = int(image_order_upper_bound)
    generators = int(generator_upper_bound)
    node_cap = int(max_recognition_nodes)
    robust_degree = int(max_robust_orbital_degree)
    state_power = int(partition_state_poly_power)
    state_cap = int(max_partition_states)
    cap = int(max_work)
    if min(
        root, n, m, parent_order, image_order, generators, node_cap,
        robust_degree, state_power, state_cap, cap,
    ) <= 0:
        raise ValueError("invalid nested primitive Johnson resource parameters")
    if robust_degree < 2:
        raise ValueError("max_robust_orbital_degree must be at least two")
    if m > n:
        raise ValueError("nested image degree exceeds the current full-string degree")
    if parent_order > factorial(n):
        raise ValueError("parent order upper bound exceeds the full symmetric group order")
    if image_order > min(parent_order, factorial(m)):
        raise ValueError("image order upper bound exceeds its parent or symmetric group order")

    stop = cap + 1
    candidates = _johnson_parameter_candidates(m)
    parameter_cover = True
    strict_progress = bool(candidates) and all(v < m for v, _ in candidates)
    max_v = max((v for v, _ in candidates), default=0)
    max_k = max((k for _, k in candidates), default=0)
    aut_order = max(
        (
            factorial(v) * (2 if v == 2 * k else 1)
            for v, k in candidates
        ),
        default=0,
    )
    action_order = bool(candidates) and image_order <= aut_order
    pair_count = comb(m, 2)

    # recognize_johnson_pair_relation can test every pair color against every
    # feasible J(v,k).  The bounded exact-orbital fallback has at most pair_count
    # orbitals and presents two colors per orbital.  This count is deliberately
    # independent of the unknown post-child subgroup and its orbital family.
    canonical_comparisons = pair_count * len(candidates)
    fallback_comparisons = (
        2 * pair_count * len(candidates) if m <= robust_degree else 0
    )
    comparisons = canonical_comparisons + fallback_comparisons
    recognition_nodes = comparisons * node_cap
    states = min(state_cap, root ** state_power) if candidates else 0
    actions = states * generators

    # Parameter enumeration and exact pair-orbit construction.  Ordered pair
    # orbit caches and the optional unordered-pair fallback each visit no more
    # than O(m^2) states per supplied generator.
    parameter_scan = _sat_mul(m, m, stop)
    pair_orbit_scan = _sat_mul(
        6 * max(1, pair_count), max(1, generators), stop
    )

    # Each exact-GI budget tick performs at most 64 refinement rounds on two
    # m-vertex relations.  256*(m+1)^3 covers row scans, signature compression,
    # witness verification, and fixed overhead.  The target automorphism group is
    # Aut(J(v,k)), bounded by 2*v! (the factor two covers v=2k complement).
    node_unit = 256 * (m + 1) ** 3
    ir_work = _sat_mul(recognition_nodes, node_unit, stop)
    if candidates:
        recognition_chain_one = _chain_bound(
            m, min(node_cap, aut_order), aut_order, m, stop
        )
        recognition_chains = _sat_mul(
            comparisons, _sat_mul(m, recognition_chain_one, stop), stop
        )
    else:
        aut_order = 0
        recognition_chains = 0
    recognition_work = 0
    for part in (
        parameter_scan,
        pair_orbit_scan,
        _sat_mul(comparisons, pair_count * (max_k + 2), stop),
        ir_work,
        recognition_chains,
    ):
        recognition_work = _sat_add(recognition_work, part, stop)

    # One successful coordinate gauge is transported at most once.  Decode and
    # exact re-induction scan all m k-subsets for every supplied generator.
    # Signature/profile construction scans both source and target and both
    # star/anti-star modes, covering the exceptional signed action.
    relation_profile_work = 0
    if candidates:
        decode = _sat_mul(
            8 * (generators + 1),
            _sat_mul(m, (max_v + 1) * (max_k + 1), stop),
            stop,
        )
        signatures = _sat_mul(
            16 * m, (max_v + 1) * (max_k + 1), stop
        )
        profile_tables = _sat_mul(
            8 * m, (max_v + max_k + 2), stop
        )
        canonical_sort = _sat_mul(
            8 * (m + max_v + 1), (m + max_v + 1), stop
        )
        for part in (decode, signatures, profile_tables, canonical_sort):
            relation_profile_work = _sat_add(
                relation_profile_work, part, stop
            )

    # A complete partition orbit has at most states*generators transitions.  The
    # implementation scans/sorts every ground cell and composes an original-domain
    # permutation on both BFS and Schreier-generator passes.
    partition_transport = 0
    if candidates:
        transition_unit = 8 * (m + max_v * max_v + max_v + 1)
        partition_transport = _sat_mul(
            2 * actions, transition_unit, stop
        )

    # Stabilizer, parity kernel, optional target conjugate, and exact parity-mode
    # subgroup construction are all original-domain raw Schreier chains.
    schreier_work = 0
    if candidates:
        raw_pairs = max(1, actions)
        chain_a = _chain_bound(m, raw_pairs, image_order, m, stop)
        chain_b = _chain_bound(m, 2 * raw_pairs, image_order, m, stop)
        chain_c = _chain_bound(m, image_order, image_order, m, stop)
        for part in (chain_a, chain_b, chain_c, chain_c):
            schreier_work = _sat_add(schreier_work, part, stop)

    # Reserve the later exact paired image/kernel/preimage lift with only the
    # pre-child parent and image order bounds.  This is the boundary that makes
    # the contract useful before the exact post-child subgroup is available.
    image_chain = _chain_bound(
        m, generators, image_order, m, stop
    )
    paired = _chain_bound(
        m, generators, parent_order, n + m, stop
    )
    kernel = _chain_bound(
        n, parent_order, parent_order, n, stop
    )
    lifts = _sat_mul(
        _sat_mul(image_order, m, stop),
        _sat_mul(parent_order, 4 * (n + m), stop),
        stop,
    )
    preimage = _chain_bound(
        n, parent_order + image_order, parent_order, n, stop
    )
    root_lift_work = 0
    if candidates:
        for part in (image_chain, paired, kernel, lifts, preimage):
            root_lift_work = _sat_add(root_lift_work, part, stop)

    total = 0
    for part in (
        recognition_work,
        relation_profile_work,
        partition_transport,
        schreier_work,
        root_lift_work,
    ):
        total = _sat_add(total, part, stop)

    root_lift = n <= root
    resource_admitted = (
        root_lift
        and bool(candidates)
        and strict_progress
        and action_order
        and total <= cap
    )
    if not root_lift:
        status = "design_nested_primitive_johnson_original_root_lift_unavailable"
        reason = "the current full-string degree exceeds the original root"
    elif not candidates:
        status = "design_nested_primitive_johnson_no_parameter_candidate"
        reason = (
            "the image degree is not C(v,k) for any 2<=k<=v/2; "
            "the existing recognizer will fail closed without entering a Johnson profile path"
        )
    elif not strict_progress:
        status = "design_nested_primitive_johnson_no_strict_ground_progress"
        reason = "a feasible Johnson parameter did not reduce to a strictly smaller ground"
    elif not action_order:
        status = "design_nested_primitive_johnson_action_order_exceeded"
        reason = (
            "the supplied image-order upper bound is too loose to certify any "
            "feasible signed Johnson action before the exact subgroup is known"
        )
    elif total > cap:
        status = "design_nested_primitive_johnson_work_cap_exceeded"
        reason = (
            "the complete recognition/profile/partition/lift envelope exceeds "
            "the finite budget before Johnson recognition starts"
        )
    else:
        status = "certified_design_nested_primitive_johnson_resource_preflight"
        reason = (
            "every feasible Johnson-gauge attempt, bounded recognition fallback, "
            "signed profile partition-orbit attempt, original-domain Schreier "
            "chain, and paired lift fits the finite caller budget before the "
            "exact post-child subgroup exists"
        )

    return NestedPrimitiveJohnsonResourceEnvelope(
        status=status,
        original_root_degree=root,
        original_degree=n,
        image_degree=m,
        parent_order_upper_bound=parent_order,
        image_order_upper_bound=image_order,
        generator_upper_bound=generators,
        johnson_parameter_candidates=candidates,
        max_ground_size=max_v,
        max_subset_size=max_k,
        pair_count=pair_count,
        recognition_comparison_upper_bound=comparisons,
        recognition_node_upper_bound=recognition_nodes,
        partition_state_upper_bound=states,
        partition_action_upper_bound=actions,
        recognition_work_upper_bound=recognition_work,
        relation_profile_work_upper_bound=relation_profile_work,
        partition_transport_work_upper_bound=partition_transport,
        schreier_work_upper_bound=schreier_work,
        original_root_lift_work_upper_bound=root_lift_work,
        work_upper_bound=total,
        max_work=cap,
        root_lift_certified=root_lift,
        johnson_parameter_cover_certified=parameter_cover,
        strict_ground_progress_certified=strict_progress,
        johnson_action_order_certified=action_order,
        resource_admitted=resource_admitted,
        exact_path_certified=False,
        reason=reason,
    )


__all__ = [
    "NestedPrimitiveJohnsonResourceEnvelope",
    "design_nested_primitive_johnson_resource_envelope",
]
