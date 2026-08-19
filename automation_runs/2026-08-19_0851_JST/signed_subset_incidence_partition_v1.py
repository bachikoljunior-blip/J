from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import log2

from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from certified_group_enumeration_v1 import enumerate_schreier_group_exact
from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import (
    SignedJohnsonGroundGenerator,
    _induce_signed_ground_generator,
    lift_primitive_johnson_to_ground_relation,
)
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from recursive_point_image_coset_intersection import right_coset_intersection_recursive


@dataclass(frozen=True)
class SignedSubsetIncidenceProof(ProofCarryingCoset):
    ground_size: int = 0
    subset_size: int = 0
    source_ground_classes: tuple[tuple[int, ...], ...] = ()
    target_ground_classes: tuple[tuple[int, ...], ...] = ()
    largest_ground_class: int = 0
    incidence_split_verified: bool = False
    signed_candidate_coset: RightCoset | None = None
    candidate_signed_subgroup_order: int = 0
    intersection_search_nodes: int = 0


def _current_domain_permutation(coordinate, p_std):
    m = len(coordinate)
    cinv = [0] * m
    for current, std in enumerate(coordinate):
        cinv[std] = current
    return tuple(cinv[p_std[coordinate[current]]] for current in range(m))


def _intrinsic_color_ids(source, target):
    values = tuple(source) + tuple(target)
    try:
        unique = tuple(sorted(set(values)))
    except (TypeError, ValueError):
        return None
    return {value: i for i, value in enumerate(unique)}


def _incidence_point_signatures(v, k, standard_values, color_ids, *, allow_complement):
    subsets = tuple(combinations(range(v), k))
    values = tuple(standard_values)
    if len(values) != len(subsets):
        raise ValueError("standard values are not a complete k-subset relation")
    q = len(color_ids)
    signatures = []
    for a in range(v):
        inside = [0] * q
        outside = [0] * q
        for subset, value in zip(subsets, values):
            bucket = inside if a in subset else outside
            bucket[color_ids[value]] += 1
        inside = tuple(inside)
        outside = tuple(outside)
        if allow_complement:
            # A global Johnson complement sends stars to anti-stars.  Forget only
            # that one global orientation bit; retain the complete two histograms.
            signatures.append(tuple(sorted((inside, outside))))
        else:
            signatures.append((inside,))
    return tuple(signatures)


def _shared_signature_colors(source_signatures, target_signatures):
    unique = tuple(sorted(set(source_signatures) | set(target_signatures)))
    ids = {sig: i for i, sig in enumerate(unique)}
    return (
        tuple(ids[s] for s in source_signatures),
        tuple(ids[s] for s in target_signatures),
    )


def _classes(colors):
    out = {}
    for point, color in enumerate(colors):
        out.setdefault(color, []).append(point)
    return tuple(tuple(xs) for _, xs in sorted(out.items()))


def _signed_extended_permutation(v, signed: SignedJohnsonGroundGenerator):
    """Faithful 2v-point action of (sigma,c): (a,b)->(sigma(a),b xor c)."""
    sigma = signed.ground_permutation
    c = int(bool(signed.complement))
    return tuple(
        (layer ^ c) * v + sigma[a]
        for layer in range(2)
        for a in range(v)
    )


def _decode_signed_extended(v, p):
    p = tuple(p)
    if len(p) != 2 * v:
        return None
    first = tuple(p[a] for a in range(v))
    c = first[0] // v
    if c not in (0, 1) or any(x // v != c for x in first):
        return None
    sigma = tuple(x % v for x in first)
    if sorted(sigma) != list(range(v)):
        return None
    for a in range(v):
        expected = (1 ^ c) * v + sigma[a]
        if p[v + a] != expected:
            return None
    return SignedJohnsonGroundGenerator(sigma, bool(c))


def _proof(status, coset, *, root_n, current_degree, ground_size, subset_size,
           exact, cost_certified, local_bound, terminal, accounting, checked,
           reason, source_classes=(), target_classes=(), largest=0, split=False,
           candidate=None, candidate_order=0, intersection_nodes=0):
    return SignedSubsetIncidenceProof(
        status,
        coset,
        "signed_subset_incidence_terminal" if exact else "signed_subset_incidence_split",
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
        subset_size=subset_size,
        source_ground_classes=tuple(source_classes),
        target_ground_classes=tuple(target_classes),
        largest_ground_class=int(largest),
        incidence_split_verified=bool(split),
        signed_candidate_coset=candidate,
        candidate_signed_subgroup_order=int(candidate_order),
        intersection_search_nodes=int(intersection_nodes),
    )


def signed_subset_incidence_string_isomorphism(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    max_class_fraction: float = 0.9,
    max_recognition_nodes: int = 500000,
    max_robust_orbital_degree: int = 128,
    max_intersection_nodes: int = 500000,
    residual_group_order_poly_power: int = 2,
    max_residual_group_order: int = 4096,
):
    """Proof-carrying first relational split for arbitrary colored J(v,k) grounds.

    For each ground point, the complete histogram of relation colors on incident
    k-subsets is label-invariant.  If the signed Johnson group contains the v=2k
    complement mode, the incident/nonincident histogram pair is normalized as an
    unordered pair because complement swaps the two globally.  This yields a
    canonical ground partition without inventing coordinates or orbital names.

    A significant partition is filtered inside a faithful 2v-point action of the
    represented signed ground group.  Thus the exceptional complement bit remains
    explicit while exact point-color candidate intersection can reuse the existing
    coset machinery.  If the residual signed subgroup is small, the complete
    colored k-subset relation is scanned and the exact SI coset is reconstructed
    on the original J(v,k) domain.  Otherwise the exact signed candidate coset and
    strict ground split are returned as certified progress for the next W1 child.
    Homogeneous incidence signatures remain fail-closed for higher local
    certificates/Split-or-Johnson refinement.
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
    if not (0.0 < max_class_fraction < 1.0):
        raise ValueError("max_class_fraction must be in (0,1)")

    lift = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=max_recognition_nodes,
        max_robust_orbital_degree=max_robust_orbital_degree,
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, min(root_n, v or m)),
            operation_kind="signed_subset_incidence_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="no strictly smaller certified signed Johnson ground is available",
        )
        return _proof(
            "undetermined_signed_subset_ground_lift", None,
            root_n=root_n, current_degree=m, ground_size=v, subset_size=k,
            exact=False, cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0, reason=lift.reason,
        )

    color_ids = _intrinsic_color_ids(
        lift.source_on_standard_subsets,
        lift.target_on_standard_subsets,
    )
    if color_ids is None:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_subset_incidence_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="relation colors lack an intrinsic order for the current exact histogram adapter",
        )
        return _proof(
            "undetermined_nonorderable_subset_colors", None,
            root_n=root_n, current_degree=m, ground_size=v, subset_size=k,
            exact=False, cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0,
            reason="fail closed rather than assign relation color IDs by vertex/encounter order",
        )

    allow_complement = any(g.complement for g in lift.lifted_generators)
    src_sig = _incidence_point_signatures(
        v, k, lift.source_on_standard_subsets, color_ids,
        allow_complement=allow_complement,
    )
    dst_sig = _incidence_point_signatures(
        v, k, lift.target_on_standard_subsets, color_ids,
        allow_complement=allow_complement,
    )
    src_colors, dst_colors = _shared_signature_colors(src_sig, dst_sig)
    src_classes = _classes(src_colors)
    dst_classes = _classes(dst_colors)
    largest = max(
        max(map(len, src_classes), default=v),
        max(map(len, dst_classes), default=v),
    )
    incidence_units = max(1, 2 * v * m * max(1, len(color_ids)))
    invariant_bound = log2(incidence_units) + 12.0 * log2(max(2, v)) + 20.0

    if Counter(src_colors) != Counter(dst_colors):
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_subset_incidence_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=invariant_bound,
            children=(), terminal_certified=True,
            reason="signed-normalized ground incidence signature multiplicities differ",
        )
        return _proof(
            "exact_empty_signed_subset_incidence_invariant", None,
            root_n=root_n, current_degree=m, ground_size=v, subset_size=k,
            exact=True, cost_certified=True, local_bound=invariant_bound,
            terminal=True, accounting=accounting, checked=0,
            reason="every represented signed Johnson isomorphism preserves the normalized incident/nonincident color histogram, so differing multiplicities certify emptiness",
            source_classes=src_classes, target_classes=dst_classes, largest=largest,
        )

    significant = (
        len(src_classes) > 1
        and len(dst_classes) > 1
        and largest <= max_class_fraction * v + 1e-12
    )
    if not significant:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_subset_incidence_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="first-order signed incidence signatures do not yield a significant ground split",
        )
        return _proof(
            "undetermined_homogeneous_subset_incidence", None,
            root_n=root_n, current_degree=m, ground_size=v, subset_size=k,
            exact=False, cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0,
            reason="W1 requires higher local certificates/coherent or Split-or-Johnson relational refinement",
            source_classes=src_classes, target_classes=dst_classes, largest=largest,
        )

    extended_generators = tuple(
        _signed_extended_permutation(v, g) for g in lift.lifted_generators
    )
    signed_chain = schreier_stabilizer_chain(
        extended_generators or (identity(2 * v),)
    )
    if signed_chain.order != group.order:
        raise AssertionError("2v signed-ground representation is not faithful to the supplied ambient group")

    src_ext_colors = src_colors + src_colors
    dst_ext_colors = dst_colors + dst_colors
    value_coset = _all_value_preserving_maps(src_ext_colors, dst_ext_colors)
    if value_coset is None:
        raise AssertionError("equal incidence-signature multiplicities must admit a point-color preserving map")
    intersection = right_coset_intersection_recursive(
        RightCoset(signed_chain, identity(2 * v)),
        value_coset,
        max_nodes=max_intersection_nodes,
    )
    if intersection.status == "empty_intersection":
        local_bound = invariant_bound + log2(max(1, intersection.search_nodes)) + 10.0 * log2(max(2, v)) + 18.0
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_subset_incidence_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=True,
            reason="exact signed-ground-group / normalized-incidence point-color candidate intersection is empty",
        )
        return _proof(
            "exact_empty_signed_incidence_partition_orbit", None,
            root_n=root_n, current_degree=m, ground_size=v, subset_size=k,
            exact=True, cost_certified=True, local_bound=local_bound,
            terminal=True, accounting=accounting, checked=0,
            reason="no represented signed Johnson element transports the canonical incidence partition",
            source_classes=src_classes, target_classes=dst_classes, largest=largest,
            split=True, intersection_nodes=intersection.search_nodes,
        )
    if intersection.status != "exact_intersection_coset" or intersection.coset is None:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_subset_incidence_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="exact signed incidence-partition candidate intersection exceeded its resource cap",
        )
        return _proof(
            "undetermined_signed_incidence_partition_intersection", None,
            root_n=root_n, current_degree=m, ground_size=v, subset_size=k,
            exact=False, cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0, reason=intersection.reason,
            source_classes=src_classes, target_classes=dst_classes, largest=largest,
            split=True, intersection_nodes=intersection.search_nodes,
        )

    candidate = intersection.coset
    residual_order = candidate.subgroup.order
    allowed_order = min(max_residual_group_order, root_n ** residual_group_order_poly_power)
    if residual_order > allowed_order:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_subset_incidence_split_pending",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="strict signed incidence split and exact 2v-point candidate coset are certified, but residual relational recursion remains",
        )
        return _proof(
            "certified_signed_subset_incidence_candidate", None,
            root_n=root_n, current_degree=m, ground_size=v, subset_size=k,
            exact=False, cost_certified=False, local_bound=0.0, terminal=False,
            accounting=accounting, checked=0,
            reason="the active W1 measure shrank to canonical ground cells; residual signed candidate subgroup is too large for exact enumeration and must recurse structurally",
            source_classes=src_classes, target_classes=dst_classes, largest=largest,
            split=True, candidate=candidate, candidate_order=residual_order,
            intersection_nodes=intersection.search_nodes,
        )

    subgroup_elements = enumerate_schreier_group_exact(
        candidate.subgroup,
        max_elements=allowed_order,
    )
    if subgroup_elements is None or len(subgroup_elements) != residual_order:
        raise AssertionError("residual signed subgroup gate admitted enumeration but exact BFS did not match")

    candidate_current = []
    matches = []
    for h in subgroup_elements:
        p_ext = compose(candidate.representative, h)
        if not candidate.contains(p_ext):
            raise AssertionError("enumerated residual signed candidate escaped its exact coset")
        signed = _decode_signed_extended(v, p_ext)
        if signed is None:
            raise AssertionError("exact signed candidate did not decode from the faithful 2v action")
        p_std = _induce_signed_ground_generator(v, k, signed.ground_permutation, signed.complement)
        q_current = _current_domain_permutation(lift.coordinate, p_std)
        if not group.contains(q_current):
            raise AssertionError("decoded signed incidence candidate escaped the original Johnson ambient group")
        candidate_current.append(q_current)
        if all(
            lift.source_on_standard_subsets[i]
            == lift.target_on_standard_subsets[p_std[i]]
            for i in range(m)
        ):
            matches.append(q_current)

    checked = len(subgroup_elements)
    execution_units = max(1, incidence_units + intersection.search_nodes + checked * max(1, m))
    local_bound = log2(execution_units) + 20.0 * log2(max(2, v)) + 12.0 * log2(max(2, m)) + 36.0

    if not matches:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_subset_incidence_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=True,
            reason="complete residual signed candidate enumeration after canonical incidence split found no full k-subset relation isomorphism",
        )
        return _proof(
            "exact_empty_signed_subset_relation", None,
            root_n=root_n, current_degree=m, ground_size=v, subset_size=k,
            exact=True, cost_certified=True, local_bound=local_bound,
            terminal=True, accounting=accounting, checked=checked,
            reason="every exact residual signed candidate was induced and tested on the complete colored k-subset relation",
            source_classes=src_classes, target_classes=dst_classes, largest=largest,
            split=True, candidate=candidate, candidate_order=residual_order,
            intersection_nodes=intersection.search_nodes,
        )

    matches = tuple(sorted(matches))
    witness = matches[0]
    translated = tuple(compose(inverse(witness), p) for p in matches)
    subgroup = schreier_stabilizer_chain(translated or (identity(m),))
    result = RightCoset(subgroup, witness)
    if subgroup.order != len(matches) or any(not result.contains(p) for p in matches):
        raise AssertionError("signed incidence matches did not reconstruct the exact original-domain coset")

    reconstructed = tuple(sorted(p for p in candidate_current if result.contains(p)))
    checked += len(candidate_current)
    if reconstructed != matches:
        raise AssertionError("reconstructed signed incidence coset differs from complete residual enumeration")

    accounting = RecurrenceAccountingNode(
        n=root_n, m=v, operation_kind="signed_subset_incidence_terminal",
        canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
        children=(), terminal_certified=True,
        reason="canonical signed incidence split, exact 2v candidate intersection, complete small residual scan, and second-pass original-domain coset audit",
    )
    return _proof(
        "exact_signed_subset_relation_coset", result,
        root_n=root_n, current_degree=m, ground_size=v, subset_size=k,
        exact=True, cost_certified=True, local_bound=local_bound,
        terminal=True, accounting=accounting, checked=checked,
        reason="the exact colored k-subset SI subset inside the original signed Johnson ambient group was reconstructed after strict ground incidence reduction",
        source_classes=src_classes, target_classes=dst_classes, largest=largest,
        split=True, candidate=candidate, candidate_order=residual_order,
        intersection_nodes=intersection.search_nodes,
    )
