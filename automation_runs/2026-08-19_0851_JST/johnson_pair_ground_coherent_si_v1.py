from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import log2

from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from certified_group_enumeration_v1 import enumerate_schreier_group_exact
from coherent_pair_refinement import coherent_refine_pair_relation
from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import (
    _induce_signed_ground_generator,
    lift_primitive_johnson_to_ground_relation,
)
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from recursive_point_image_coset_intersection import right_coset_intersection_recursive


@dataclass(frozen=True)
class JohnsonPairGroundCoherentProof(ProofCarryingCoset):
    ground_size: int = 0
    source_point_classes: tuple[tuple[int, ...], ...] = ()
    target_point_classes: tuple[tuple[int, ...], ...] = ()
    largest_ground_class: int = 0
    ground_split_verified: bool = False
    candidate_ground_order: int = 0
    intersection_search_nodes: int = 0


def _current_domain_permutation(coordinate, p_std):
    m = len(coordinate)
    cinv = [0] * m
    for current, std in enumerate(coordinate):
        cinv[std] = current
    return tuple(cinv[p_std[coordinate[current]]] for current in range(m))


def _joint_intrinsic_color_ids(source, target):
    """Map intrinsically orderable/hashable color atoms to shared integer IDs.

    The current coherent-pair implementation requires integer pair weights.  This
    adapter deliberately fails closed for color objects without an intrinsic total
    order instead of using vertex-order-dependent first occurrence or repr-based
    naming.  Integers/strings/tuples of comparable atoms work directly.
    """
    values = tuple(source) + tuple(target)
    try:
        unique = tuple(sorted(set(values)))
    except (TypeError, ValueError):
        return None
    ids = {value: i for i, value in enumerate(unique)}
    return ids


def _pair_weights_from_standard_values(v, standard_values, color_ids):
    subsets = tuple(combinations(range(v), 2))
    if len(subsets) != len(standard_values):
        raise ValueError("standard values are not a complete J(v,2) relation")
    return tuple((subsets[i], color_ids[standard_values[i]]) for i in range(len(subsets)))


def _proof(status, coset, *, root_n, current_degree, ground_size, exact,
           cost_certified, local_bound, terminal, accounting, checked, reason,
           source_classes=(), target_classes=(), largest=0, split=False,
           candidate_order=0, intersection_nodes=0):
    return JohnsonPairGroundCoherentProof(
        status,
        coset,
        "johnson_pair_ground_coherent_terminal" if exact else "johnson_pair_ground_coherent_split",
        root_n,
        current_degree,
        True,
        exact,
        cost_certified,
        local_bound,
        terminal,
        (),
        accounting,
        checked,
        reason,
        ground_size=ground_size,
        source_point_classes=tuple(source_classes),
        target_point_classes=tuple(target_classes),
        largest_ground_class=int(largest),
        ground_split_verified=bool(split),
        candidate_ground_order=int(candidate_order),
        intersection_search_nodes=int(intersection_nodes),
    )


def johnson_pair_ground_coherent_string_isomorphism(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    max_class_fraction: float = 0.9,
    max_refinement_rounds: int = 128,
    max_recognition_nodes: int = 500000,
    max_robust_orbital_degree: int = 128,
    max_intersection_nodes: int = 500000,
    residual_group_order_poly_power: int = 2,
    max_residual_group_order: int = 4096,
):
    """Exact/progressive W1 path for colored J(v,2) relations on a smaller ground.

    After the rev175/rev176 faithful Johnson lift, a J(v,2) string is exactly an
    edge-colored complete graph on the v-point ground.  Stable 2-WL/coherent pair
    refinement of those *actual relation colors* yields a canonical ground-point
    partition.  If source and target partition invariants disagree, SI is empty.
    If a significant split exists, we intersect the lifted ambient ground group
    with all source-to-target point-color maps exactly.

    When the resulting candidate subgroup is small, we enumerate only that
    residual subgroup and test the complete edge relation, reconstructing the
    exact answer back on the original J(v,2) domain.  If the residual subgroup is
    still large, the verified ground split and exact candidate coset are retained
    as real progress but the full relational SI claim remains fail-closed.  The
    homogeneous coherent case is intentionally left for the next Split-or-Johnson
    / local-certificate W1 child.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if len(source) != m or len(target) != m:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = m
    if root_n < m:
        raise ValueError("root_n must dominate current Johnson domain")

    lift = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=max_recognition_nodes,
        max_robust_orbital_degree=max_robust_orbital_degree,
    )
    v = int(lift.ground_size)
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, min(root_n, v or m)),
            operation_kind="johnson_pair_ground_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="a strictly smaller certified Johnson ground was not available",
        )
        return _proof(
            "undetermined_johnson_pair_ground_lift", None,
            root_n=root_n, current_degree=m, ground_size=v, exact=False,
            cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0, reason=lift.reason,
        )
    if lift.subset_size != 2:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="johnson_pair_ground_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="coherent pair-ground adapter currently handles only k=2 relations",
        )
        return _proof(
            "undetermined_higher_arity_signed_ground_relation", None,
            root_n=root_n, current_degree=m, ground_size=v, exact=False,
            cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0,
            reason="higher-k colored subset relations require the logarithmic-arity/local-certificate W1 path",
        )
    if any(g.complement for g in lift.lifted_generators):
        raise AssertionError("a large-ground J(v,2) action cannot have the v=2k complement mode")

    color_ids = _joint_intrinsic_color_ids(
        lift.source_on_standard_subsets,
        lift.target_on_standard_subsets,
    )
    if color_ids is None:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="johnson_pair_ground_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="relation colors lack the intrinsic ordering required by the current integer-weight coherent-refinement adapter",
        )
        return _proof(
            "undetermined_nonorderable_relation_colors", None,
            root_n=root_n, current_degree=m, ground_size=v, exact=False,
            cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0,
            reason="fail closed rather than introduce label/order-dependent color IDs",
        )

    src_ref = coherent_refine_pair_relation(
        v,
        _pair_weights_from_standard_values(v, lift.source_on_standard_subsets, color_ids),
        max_class_fraction=max_class_fraction,
        max_rounds=max_refinement_rounds,
    )
    dst_ref = coherent_refine_pair_relation(
        v,
        _pair_weights_from_standard_values(v, lift.target_on_standard_subsets, color_ids),
        max_class_fraction=max_class_fraction,
        max_rounds=max_refinement_rounds,
    )
    if src_ref.status == "undetermined_round_limit" or dst_ref.status == "undetermined_round_limit":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="johnson_pair_ground_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="ground coherent refinement exceeded its explicit stabilization round cap",
        )
        return _proof(
            "undetermined_ground_coherent_round_limit", None,
            root_n=root_n, current_degree=m, ground_size=v, exact=False,
            cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0, reason=accounting.reason,
        )

    src_counter = Counter(src_ref.point_colors)
    dst_counter = Counter(dst_ref.point_colors)
    invariant_cost = max(1, v * v * max(1, src_ref.refinement_rounds + dst_ref.refinement_rounds))
    invariant_bound = log2(invariant_cost) + 12.0 * log2(max(2, v)) + 20.0
    if src_counter != dst_counter:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="johnson_pair_ground_coherent_terminal",
            canonical=True, cost_certified=True,
            local_log2_cost_bound=invariant_bound,
            children=(), terminal_certified=True,
            reason="stable coherent diagonal-color multiplicities differ on the two ground relations",
        )
        return _proof(
            "exact_empty_ground_coherent_invariant", None,
            root_n=root_n, current_degree=m, ground_size=v, exact=True,
            cost_certified=True, local_bound=invariant_bound, terminal=True,
            accounting=accounting, checked=0,
            reason="a relation isomorphism must preserve stable 2-WL diagonal colors, so the differing multiplicities certify emptiness",
            source_classes=src_ref.color_classes, target_classes=dst_ref.color_classes,
            largest=max(src_ref.largest_class, dst_ref.largest_class),
        )

    significant = src_ref.significant_split and dst_ref.significant_split
    largest = max(src_ref.largest_class, dst_ref.largest_class)
    if not significant:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="johnson_pair_ground_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="the actual colored pair relation remains homogeneous/non-significantly split after stable coherent refinement",
        )
        return _proof(
            "undetermined_homogeneous_ground_coherent_relation", None,
            root_n=root_n, current_degree=m, ground_size=v, exact=False,
            cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0,
            reason="W1 must continue with Split-or-Johnson/local-certificate relational recursion",
            source_classes=src_ref.color_classes, target_classes=dst_ref.color_classes,
            largest=largest,
        )

    ground_group = schreier_stabilizer_chain(
        [g.ground_permutation for g in lift.lifted_generators] or [identity(v)]
    )
    if ground_group.order != group.order:
        raise AssertionError("k=2 Johnson ground lift is expected to be faithful without complement kernel")

    value_coset = _all_value_preserving_maps(src_ref.point_colors, dst_ref.point_colors)
    if value_coset is None:
        raise AssertionError("equal coherent point-color multiplicities must admit a value-preserving map")
    intersection = right_coset_intersection_recursive(
        RightCoset(ground_group, identity(v)),
        value_coset,
        max_nodes=max_intersection_nodes,
    )
    if intersection.status == "empty_intersection":
        local_bound = invariant_bound + log2(max(1, intersection.search_nodes)) + 8.0 * log2(max(2, v)) + 16.0
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="johnson_pair_ground_coherent_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=True,
            reason="exact lifted-ground-group / coherent-point-color coset intersection is empty",
        )
        return _proof(
            "exact_empty_ground_partition_orbit", None,
            root_n=root_n, current_degree=m, ground_size=v, exact=True,
            cost_certified=True, local_bound=local_bound, terminal=True,
            accounting=accounting, checked=0,
            reason="no ambient Johnson ground permutation transports the canonical coherent point partition",
            source_classes=src_ref.color_classes, target_classes=dst_ref.color_classes,
            largest=largest, split=True, intersection_nodes=intersection.search_nodes,
        )
    if intersection.status != "exact_intersection_coset" or intersection.coset is None:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="johnson_pair_ground_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="exact ground partition candidate intersection exceeded its resource bound",
        )
        return _proof(
            "undetermined_ground_partition_intersection", None,
            root_n=root_n, current_degree=m, ground_size=v, exact=False,
            cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0,
            reason=intersection.reason,
            source_classes=src_ref.color_classes, target_classes=dst_ref.color_classes,
            largest=largest, split=True, intersection_nodes=intersection.search_nodes,
        )

    candidate = intersection.coset
    residual_order = candidate.subgroup.order
    allowed_order = min(max_residual_group_order, root_n ** residual_group_order_poly_power)
    if residual_order > allowed_order:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="johnson_pair_ground_split_pending",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="canonical coherent ground split and exact partition-respecting candidate coset are certified, but residual relational recursion remains",
        )
        return _proof(
            "certified_ground_coherent_split_candidate", None,
            root_n=root_n, current_degree=m, ground_size=v, exact=False,
            cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0,
            reason="strict ground-point split is real progress; the remaining candidate subgroup is too large for exact residual enumeration and must recurse by cells/local certificates",
            source_classes=src_ref.color_classes, target_classes=dst_ref.color_classes,
            largest=largest, split=True, candidate_order=residual_order,
            intersection_nodes=intersection.search_nodes,
        )

    subgroup_elements = enumerate_schreier_group_exact(
        candidate.subgroup,
        max_elements=allowed_order,
    )
    if subgroup_elements is None or len(subgroup_elements) != residual_order:
        raise AssertionError("residual group-order gate admitted enumeration but exact BFS did not match")

    matches = []
    candidate_current = []
    for h in subgroup_elements:
        sigma = compose(candidate.representative, h)
        p_std = _induce_signed_ground_generator(v, 2, sigma, False)
        q_current = _current_domain_permutation(lift.coordinate, p_std)
        if not group.contains(q_current):
            raise AssertionError("ground partition candidate escaped the original Johnson ambient group")
        candidate_current.append(q_current)
        if all(
            lift.source_on_standard_subsets[i]
            == lift.target_on_standard_subsets[p_std[i]]
            for i in range(m)
        ):
            matches.append(q_current)

    checked = len(subgroup_elements)
    execution_units = max(1, checked * max(1, m) + intersection.search_nodes + invariant_cost)
    local_bound = log2(execution_units) + 18.0 * log2(max(2, v)) + 12.0 * log2(max(2, m)) + 32.0

    if not matches:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="johnson_pair_ground_coherent_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=True,
            reason="complete residual candidate-subgroup enumeration after canonical coherent ground split found no full pair-relation isomorphism",
        )
        return _proof(
            "exact_empty_johnson_pair_ground_relation", None,
            root_n=root_n, current_degree=m, ground_size=v, exact=True,
            cost_certified=True, local_bound=local_bound, terminal=True,
            accounting=accounting, checked=checked,
            reason="every partition-respecting residual candidate was tested on the complete colored pair relation",
            source_classes=src_ref.color_classes, target_classes=dst_ref.color_classes,
            largest=largest, split=True, candidate_order=residual_order,
            intersection_nodes=intersection.search_nodes,
        )

    matches = tuple(sorted(matches))
    witness = matches[0]
    translated = tuple(compose(inverse(witness), p) for p in matches)
    subgroup = schreier_stabilizer_chain(translated or (identity(m),))
    result = RightCoset(subgroup, witness)
    if subgroup.order != len(matches) or any(not result.contains(p) for p in matches):
        raise AssertionError("pair-ground residual matches did not reconstruct the exact original-domain coset")

    reconstructed = tuple(sorted(p for p in candidate_current if result.contains(p)))
    checked += len(candidate_current)
    if reconstructed != matches:
        raise AssertionError("reconstructed pair-ground coset differs from complete residual enumeration")

    accounting = RecurrenceAccountingNode(
        n=root_n, m=v, operation_kind="johnson_pair_ground_coherent_terminal",
        canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
        children=(), terminal_certified=True,
        reason="canonical coherent ground split, exact candidate intersection, complete small residual scan, and second-pass coset audit",
    )
    return _proof(
        "exact_johnson_pair_ground_relation_coset", result,
        root_n=root_n, current_degree=m, ground_size=v, exact=True,
        cost_certified=True, local_bound=local_bound, terminal=True,
        accounting=accounting, checked=checked,
        reason="the exact pair-relation SI subset inside the original Johnson ambient group was reconstructed after a strictly smaller canonical ground split",
        source_classes=src_ref.color_classes, target_classes=dst_ref.color_classes,
        largest=largest, split=True, candidate_order=residual_order,
        intersection_nodes=intersection.search_nodes,
    )
