from __future__ import annotations

from ambient_design_tuple_transport_v1 import pair_design_witnesses_inside_ambient_action
from bipartite_design_recurrence_gate_v1 import certify_complete_design_cover_recurrence_progress
from permutation_group_schreier import identity, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v1 import validate_quasipoly_recurrence_tree


def _edges(hyperedges):
    return {(a, b) for a, edge in enumerate(hyperedges) for b in edge}


def _trivial(n):
    return schreier_stabilizer_chain([identity(n)])


def _disconnected_four_cycles():
    return [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
    ]


def _cycle11():
    return [(i, (i + 1) % 11) for i in range(11)]


def test_complete_imprimitive_design_cover_has_strict_aux_shrink_plan():
    incidence = _edges(_disconnected_four_cycles())
    cover = pair_design_witnesses_inside_ambient_action(
        _trivial(8),
        8,
        8,
        incidence,
        incidence,
        alpha=0.75,
        max_tuple_states=200,
        max_twl_rounds=32,
        max_twl_work_units=10_000_000,
        max_branch_pairs=200,
    )
    assert cover.status == "certified_ambient_design_witness_coset_cover"
    gate = certify_complete_design_cover_recurrence_progress(
        cover,
        root_n=64,
        alpha=0.75,
        max_tuple_states=200,
        max_twl_rounds=32,
        max_twl_work_units=10_000_000,
    )
    assert gate.status == "certified_complete_design_aux_shrink_plan"
    assert gate.complete_structural_progress
    assert gate.unresolved_branches == 0
    assert gate.progress_branches == 1
    assert gate.max_child_aux_size == 2
    assert gate.max_child_aux_size <= 0.75 * 8
    assert gate.accounting_root is not None
    assert gate.accounting_root.operation_kind == "aux_shrink"
    assert tuple(edge.node.m for edge in gate.accounting_root.children) == (2, 2, 2, 2)

    # Strict boundary: progress measures are proved, but downstream exact child SI
    # proofs are placeholders, so the global accounting validator must still reject.
    validation = validate_quasipoly_recurrence_tree(gate.accounting_root)
    assert not validation.certified
    assert validation.status == "uncertified_local_cost"


def test_cycle11_surviving_upcc_branch_remains_explicitly_unresolved():
    incidence = _edges(_cycle11())
    cover = pair_design_witnesses_inside_ambient_action(
        _trivial(11),
        11,
        11,
        incidence,
        incidence,
        alpha=0.75,
        max_tuple_states=200,
        max_twl_rounds=32,
        max_twl_work_units=10_000_000,
        max_branch_pairs=200,
    )
    assert cover.status == "certified_ambient_design_witness_coset_cover"
    gate = certify_complete_design_cover_recurrence_progress(
        cover,
        root_n=32,
        alpha=0.75,
        max_tuple_states=200,
        max_twl_rounds=32,
        max_twl_work_units=10_000_000,
    )
    assert gate.status == "requires_full_split_or_johnson_on_surviving_design_branch"
    assert not gate.complete_structural_progress
    assert gate.unresolved_branches == 1
    assert gate.progress_branches == 0
    assert gate.accounting_root is None
    assert gate.records[0].source_progress is not None
    assert gate.records[0].source_progress.status == "requires_full_split_or_johnson"


def test_unary_half_bounded_relation_emits_progress_but_not_fake_child_closure():
    edges = {(0, 0), (1, 1)}
    cover = pair_design_witnesses_inside_ambient_action(
        _trivial(4), 2, 4, edges, edges, alpha=0.75
    )
    assert cover.status == "certified_unary_ambient_partition_coset"
    gate = certify_complete_design_cover_recurrence_progress(
        cover, root_n=16, alpha=0.75
    )
    assert gate.status == "certified_complete_unary_aux_shrink_plan"
    assert gate.complete_structural_progress
    assert gate.max_child_aux_size == 2
    assert gate.accounting_root is not None
    validation = validate_quasipoly_recurrence_tree(gate.accounting_root)
    assert not validation.certified
    assert validation.status == "uncertified_local_cost"
