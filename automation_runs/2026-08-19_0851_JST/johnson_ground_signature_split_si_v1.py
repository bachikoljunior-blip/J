from __future__ import annotations

from collections import Counter
from math import log2

from canonical_local_partition_iso_coset_v1 import _target_stabilizer
from canonical_partition_transporter_v1 import canonical_partition_transporter
from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from proof_carrying_si_v1 import ProofCarryingCoset, _uncertified_leaf
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


def _hist(values):
    try:
        return frozenset(Counter(values).items())
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc


def _signed_ground_signatures(v, k, standard_subsets, values):
    signatures = []
    for a in range(v):
        inside = [values[i] for i, subset in enumerate(standard_subsets) if a in subset]
        outside = [values[i] for i, subset in enumerate(standard_subsets) if a not in subset]
        # Complement, when v=2k, exchanges star and anti-star globally.  Using
        # an unordered pair therefore remains invariant under both Johnson modes.
        signatures.append(frozenset((_hist(inside), _hist(outside))))
    return tuple(signatures)


def _cells_by_reference_order(source_signatures, target_signatures):
    order = []
    seen = set()
    for sig in source_signatures:
        if sig not in seen:
            seen.add(sig)
            order.append(sig)
    if set(target_signatures) != seen:
        return None
    src = tuple(tuple(i for i, sig in enumerate(source_signatures) if sig == key) for key in order)
    dst = tuple(tuple(i for i, sig in enumerate(target_signatures) if sig == key) for key in order)
    if tuple(map(len, src)) != tuple(map(len, dst)):
        return None
    return src, dst


def _signed_subset_profile(subset, cells, v, k):
    counts = tuple(sum(1 for x in subset if x in cell) for cell in cells)
    if v == 2 * k:
        complement_counts = tuple(len(cell) - count for cell, count in zip(cells, counts))
        return frozenset((counts, complement_counts))
    return counts


def _subset_profile_cells(v, k, standard_subsets, source_ground_cells, target_ground_cells, coordinate):
    source_profiles = tuple(
        _signed_subset_profile(subset, source_ground_cells, v, k)
        for subset in standard_subsets
    )
    target_profiles = tuple(
        _signed_subset_profile(subset, target_ground_cells, v, k)
        for subset in standard_subsets
    )
    ordered = _cells_by_reference_order(source_profiles, target_profiles)
    if ordered is None:
        return None
    source_std_cells, target_std_cells = ordered

    current_by_std = [None] * len(coordinate)
    for current, std in enumerate(coordinate):
        current_by_std[std] = current
    source_current = tuple(
        tuple(sorted(current_by_std[std] for std in cell)) for cell in source_std_cells
    )
    target_current = tuple(
        tuple(sorted(current_by_std[std] for std in cell)) for cell in target_std_cells
    )
    return source_current, target_current


def _charge_child(child: ProofCarryingCoset, *, orbit_states: int, m: int, v: int, recognition_nodes: int):
    if not child.exact or not child.local_cost_certified:
        return child
    execution_units = max(1, int(orbit_states) + int(recognition_nodes) + m * max(1, v))
    extra = log2(execution_units) + 18.0 * log2(max(2, m)) + 12.0 * log2(max(2, v)) + 28.0
    old = child.accounting
    accounting = RecurrenceAccountingNode(
        n=old.n,
        m=old.m,
        operation_kind=old.operation_kind,
        canonical=old.canonical,
        cost_certified=old.cost_certified,
        local_log2_cost_bound=old.local_log2_cost_bound + extra,
        children=old.children,
        terminal_certified=old.terminal_certified,
        reason=old.reason + "; rev176 signed-ground incidence split charge added",
    )
    return ProofCarryingCoset(
        "exact_johnson_ground_signature_split_" + child.status,
        child.coset,
        child.operation_kind,
        child.root_n,
        child.domain_size,
        child.canonical,
        child.exact,
        child.local_cost_certified,
        child.local_log2_cost_bound + extra,
        child.terminal_certified,
        child.children,
        accounting,
        child.permutation_candidates_checked,
        "certified signed-ground incidence signatures induced a nontrivial current-domain partition; exact candidate recursion returned the final SI result",
    )


def johnson_ground_signature_split_string_isomorphism(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
    max_recognition_nodes: int = 500000,
    max_partition_states: int = 200000,
    max_explicit_ground_degree: int = 8,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
):
    """Use a complement-safe ground incidence signature to force structural SI progress.

    The input must already expose an exact Johnson coordinate system.  Ground
    points are colored by the unordered pair of source/target value histograms on
    their star and anti-star; this is invariant under ordinary Johnson ground
    permutations and under the exceptional v=2k complement mode.  A nontrivial
    ground split induces a complement-safe partition of k-subset positions by
    their intersection-count profile.  We compute the exact ambient transporter
    coset for that partition and recurse on it.  Its subgroup preserves multiple
    current-domain cells setwise, so the recursive candidate subgroup is
    intransitive and cannot return to this primitive Johnson branch.

    Homogeneous ground signatures remain a typed fail-closed W1 leaf for deeper
    Design-Lemma/local-certificate treatment.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if root_n < m or root_n <= 0:
        raise ValueError("root_n must dominate the current degree")
    if len(source) != m or len(target) != m:
        raise ValueError("string/group degree mismatch")

    lift = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=max_recognition_nodes,
    )
    if lift.status != "exact_johnson_ground_relational_lift":
        return _uncertified_leaf(
            "undetermined_johnson_ground_signature_no_certified_coordinates",
            root_n=root_n,
            m=m,
            reason=lift.reason,
        )

    v, k = lift.ground_size, lift.subset_size
    from itertools import combinations
    standard_subsets = tuple(combinations(range(v), k))
    src_signatures = _signed_ground_signatures(v, k, standard_subsets, lift.source_on_standard_subsets)
    dst_signatures = _signed_ground_signatures(v, k, standard_subsets, lift.target_on_standard_subsets)
    ground_cells = _cells_by_reference_order(src_signatures, dst_signatures)
    if ground_cells is None:
        local = log2(max(1, v * m + lift.recognition_search_nodes)) + 20.0 * log2(max(2, m)) + 24.0
        accounting = RecurrenceAccountingNode(
            n=root_n, m=m, operation_kind="johnson_ground_signature_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local,
            children=(), terminal_certified=True,
            reason="signed-ground incidence signature multiplicities differ",
        )
        return ProofCarryingCoset(
            "exact_empty_johnson_ground_signature_mismatch", None,
            "johnson_ground_signature_terminal", root_n, m, True, True, True,
            local, True, (), accounting, 0,
            "a signed Johnson isomorphism must preserve the star/anti-star incidence signature multiset",
        )

    src_ground_cells, dst_ground_cells = ground_cells
    if len(src_ground_cells) <= 1:
        return _uncertified_leaf(
            "undetermined_homogeneous_johnson_ground_signature",
            root_n=root_n,
            m=m,
            reason="all ground points have the same complement-safe incidence signature; deeper relational/local-certificate recursion is required",
        )

    profile_cells = _subset_profile_cells(
        v, k, standard_subsets, src_ground_cells, dst_ground_cells, lift.coordinate
    )
    if profile_cells is None:
        local = log2(max(1, v * m + lift.recognition_search_nodes)) + 20.0 * log2(max(2, m)) + 24.0
        accounting = RecurrenceAccountingNode(
            n=root_n, m=m, operation_kind="johnson_ground_signature_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local,
            children=(), terminal_certified=True,
            reason="ground signature cells induce different signed subset-profile multiplicities",
        )
        return ProofCarryingCoset(
            "exact_empty_johnson_subset_profile_mismatch", None,
            "johnson_ground_signature_terminal", root_n, m, True, True, True,
            local, True, (), accounting, 0,
            "a signed Johnson isomorphism must preserve the induced complement-safe subset-profile partition",
        )

    src_cells, dst_cells = profile_cells
    if len(src_cells) <= 1 or max(map(len, src_cells)) >= m:
        return _uncertified_leaf(
            "undetermined_johnson_ground_split_did_not_reach_subset_domain",
            root_n=root_n,
            m=m,
            reason="ground signatures split but the complement-safe k-subset profile remained homogeneous",
        )

    transport = canonical_partition_transporter(
        group,
        tuple((i,) for i in range(m)),
        src_cells,
        dst_cells,
        max_states=max_partition_states,
    )
    if transport.status == "undetermined_partition_orbit_limit":
        return _uncertified_leaf(
            "undetermined_johnson_signature_partition_orbit_limit",
            root_n=root_n,
            m=m,
            reason=transport.reason,
        )
    if transport.status != "partition_transporter_coset":
        local = log2(max(1, transport.orbit_states + v * m + lift.recognition_search_nodes)) + 22.0 * log2(max(2, m)) + 28.0
        accounting = RecurrenceAccountingNode(
            n=root_n, m=m, operation_kind="johnson_ground_signature_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local,
            children=(), terminal_certified=True,
            reason="exact ambient partition orbit contains no transporter",
        )
        return ProofCarryingCoset(
            "exact_empty_johnson_signature_partition_orbit", None,
            "johnson_ground_signature_terminal", root_n, m, True, True, True,
            local, True, (), accounting, 0,
            "no ambient group element maps the source signed-ground subset-profile cells to the target cells",
        )

    target_stabilizer = _target_stabilizer(transport.source_stabilizer, transport.transporter)
    if len(tuple(cell for cell in dst_cells if cell)) <= 1:
        return _uncertified_leaf(
            "undetermined_invalid_johnson_signature_stabilizer",
            root_n=root_n,
            m=m,
            reason="partition unexpectedly failed to expose multiple target cells",
        )
    candidate = RightCoset(target_stabilizer, transport.transporter)

    # Lazy import avoids a module cycle.  Because target_stabilizer preserves the
    # multiple profile cells setwise, this child subgroup is intransitive on the
    # current k-subset domain, so the recursive call cannot revisit this primitive
    # Johnson signature branch.
    from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2
    child = candidate_coset_string_isomorphism_u2(
        candidate,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        max_explicit_ground_degree=max_explicit_ground_degree,
    )
    return _charge_child(
        child,
        orbit_states=transport.orbit_states,
        m=m,
        v=v,
        recognition_nodes=lift.recognition_search_nodes,
    )
