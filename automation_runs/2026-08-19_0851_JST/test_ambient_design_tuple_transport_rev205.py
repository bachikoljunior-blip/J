from __future__ import annotations

from ambient_design_tuple_transport_v1 import (
    ordered_tuple_transporter,
    pair_design_witnesses_inside_ambient_action,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _edges(hyperedges):
    return {(a, b) for a, edge in enumerate(hyperedges) for b in edge}


def _cycle5():
    return [(i, (i + 1) % 5) for i in range(5)]


def _cyclic_group(n):
    cycle = tuple((i + 1) % n for i in range(n))
    return schreier_stabilizer_chain([cycle])


def _trivial_group(n):
    return schreier_stabilizer_chain([identity(n)])


def test_ordered_tuple_transporter_is_exact_inside_cyclic_group():
    group = _cyclic_group(5)
    got = ordered_tuple_transporter(group, (0, 1), (2, 3))
    assert got.status == "ordered_tuple_transporter_coset"
    assert got.coset is not None
    assert got.coset.representative[0] == 2
    assert got.coset.representative[1] == 3
    assert got.coset.subgroup.order == 1
    assert got.exact


def test_ordered_tuple_transporter_rejects_unreachable_pair():
    group = _cyclic_group(5)
    got = ordered_tuple_transporter(group, (0, 1), (0, 2))
    assert got.status == "no_ordered_tuple_transporter"
    assert got.coset is None
    assert got.exact


def test_cycle5_design_cover_is_filtered_by_trivial_ambient_group():
    edges = _edges(_cycle5())
    got = pair_design_witnesses_inside_ambient_action(
        _trivial_group(5),
        5,
        5,
        edges,
        edges,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_work_units=2_000_000,
    )
    assert got.status == "certified_ambient_design_witness_coset_cover"
    assert got.wiring.status == "certified_relation_design_branch_plan"
    assert got.original_branch_count == 25
    assert got.surviving_branch_count == 5
    assert all(branch.source_tuple == branch.target_tuple for branch in got.branches)
    assert all(branch.stabilizer_order == 1 for branch in got.branches)
    assert got.parent_provenance_verified
    assert got.ambient_pairing_complete
    assert not got.full_string_integration_complete
    assert got.exact and not got.exact_empty


def test_cycle5_design_cover_keeps_all_singleton_pairs_under_transitive_cyclic_group():
    edges = _edges(_cycle5())
    got = pair_design_witnesses_inside_ambient_action(
        _cyclic_group(5),
        5,
        5,
        edges,
        edges,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_work_units=2_000_000,
    )
    assert got.status == "certified_ambient_design_witness_coset_cover"
    assert got.original_branch_count == 25
    assert got.surviving_branch_count == 25
    assert got.ambient_pairing_complete and got.exact


def test_unary_partition_gets_exact_ambient_transporter():
    source = {(0, 0), (1, 1)}
    target = {(0, 1), (1, 2)}
    got = pair_design_witnesses_inside_ambient_action(
        _cyclic_group(4), 2, 4, source, target
    )
    assert got.status == "certified_unary_ambient_partition_coset"
    assert got.unary_transport is not None
    assert got.unary_transport.status == "partition_transporter_coset"
    assert got.ambient_pairing_complete and got.exact
    assert not got.full_string_integration_complete


def test_unary_partition_is_exact_empty_when_trivial_ambient_group_cannot_move_it():
    source = {(0, 0), (1, 1)}
    target = {(0, 1), (1, 2)}
    got = pair_design_witnesses_inside_ambient_action(
        _trivial_group(4), 2, 4, source, target
    )
    assert got.status == "exact_empty_unary_ambient_partition"
    assert got.exact_empty and got.exact
    assert got.ambient_pairing_complete


def test_rev204_parent_mismatch_remains_exact_empty_before_ambient_filtering():
    source = _edges(_cycle5())
    target_hyperedges = list(_cycle5())
    target_hyperedges[-1] = target_hyperedges[0]
    got = pair_design_witnesses_inside_ambient_action(
        _cyclic_group(5), 5, 5, source, _edges(target_hyperedges)
    )
    assert got.status == "exact_empty_rev204_parent"
    assert got.exact_empty and got.exact


def test_ambient_group_degree_must_match_right_ground():
    edges = _edges(_cycle5())
    try:
        pair_design_witnesses_inside_ambient_action(
            _trivial_group(4), 5, 5, edges, edges
        )
    except ValueError as exc:
        assert "degree" in str(exc)
    else:
        raise AssertionError("expected ambient-degree validation failure")
