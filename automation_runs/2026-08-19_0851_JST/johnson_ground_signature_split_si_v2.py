from __future__ import annotations

from math import log2

from canonical_local_partition_iso_coset_v1 import _target_stabilizer
from canonical_partition_transporter_v1 import canonical_partition_transporter
from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from johnson_ground_signature_split_si_v1 import (
    _cells_by_reference_order,
    _charge_child,
    _signed_ground_signatures,
    _subset_profile_cells,
)
from proof_carrying_si_v1 import ProofCarryingCoset, _uncertified_leaf
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


def johnson_ground_signature_split_string_isomorphism_v2(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
    max_recognition_nodes: int = 500000,
    max_partition_states: int = 200000,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
):
    """Proof-carrying W1 split branch for a certified large-ground Johnson action.

    This is the corrected rev176 entrypoint.  It preserves the caller's exact
    candidate-recursion parameters and never passes a nonexistent ground-cap
    keyword into U2.  The structural construction is otherwise the rev176 v1
    signed star/anti-star incidence split.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if root_n < m or root_n <= 0:
        raise ValueError("root_n must dominate the current degree")
    if len(source) != m or len(target) != m:
        raise ValueError("string/group degree mismatch")

    lift = lift_primitive_johnson_to_ground_relation(
        group, source, target, max_recognition_nodes=max_recognition_nodes
    )
    if lift.status != "exact_johnson_ground_relational_lift":
        return _uncertified_leaf(
            "undetermined_johnson_ground_signature_no_certified_coordinates",
            root_n=root_n, m=m, reason=lift.reason,
        )

    from itertools import combinations
    v, k = lift.ground_size, lift.subset_size
    standard_subsets = tuple(combinations(range(v), k))
    src_signatures = _signed_ground_signatures(
        v, k, standard_subsets, lift.source_on_standard_subsets
    )
    dst_signatures = _signed_ground_signatures(
        v, k, standard_subsets, lift.target_on_standard_subsets
    )
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
            root_n=root_n, m=m,
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
            root_n=root_n, m=m,
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
            root_n=root_n, m=m, reason=transport.reason,
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

    target_stabilizer = _target_stabilizer(
        transport.source_stabilizer, transport.transporter
    )
    candidate = RightCoset(target_stabilizer, transport.transporter)

    # Multiple profile cells are preserved setwise by target_stabilizer.  Hence
    # this child is intransitive on the current Johnson domain and U2 dispatches
    # to orbit recursion instead of returning to the primitive Johnson branch.
    from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2
    child = candidate_coset_string_isomorphism_u2(
        candidate,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
    )
    return _charge_child(
        child,
        orbit_states=transport.orbit_states,
        m=m,
        v=v,
        recognition_nodes=lift.recognition_search_nodes,
    )
