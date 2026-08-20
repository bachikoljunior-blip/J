import pytest

from bipartite_twin_split_progress_v1 import (
    certify_bipartite_twin_split_progress,
    make_twin_split_accounting_node,
)
from quasipoly_structural_recurrence_accounting_v2 import (
    PHASE_UPCC,
    StructuralRecurrenceAccountingNode,
    validate_structural_quasipoly_recurrence_tree,
)


def _terminal(n, m):
    return StructuralRecurrenceAccountingNode(
        n=n,
        m=m,
        structural_phase=PHASE_UPCC,
        operation_kind="terminal",
        canonical=True,
        cost_certified=True,
        progress_certified=True,
        local_log2_cost_bound=1.0,
        children=(),
        terminal_certified=True,
        reason="exact synthetic continuation terminal",
    )


def test_rev199_pair_blocks_are_an_exact_visible_auxiliary_split():
    edges = {(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2)}
    got = certify_bipartite_twin_split_progress(6, 3, edges, alpha=0.75)
    assert got.status == "certified_bipartite_twin_aux_shrink"
    assert got.theorem_input_gate
    assert got.progress_certified
    assert got.twin_cell_sizes == (2, 2, 2)
    assert got.largest_twin_cell == 2
    assert got.canonical_partition and got.exact_partition


def test_dense_complement_has_the_same_visible_twin_split():
    sparse = {(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2)}
    dense = {(a, b) for a in range(6) for b in range(3)} - sparse
    a = certify_bipartite_twin_split_progress(6, 3, sparse, alpha=0.75)
    b = certify_bipartite_twin_split_progress(6, 3, dense, alpha=0.75)
    assert a.twin_cell_sizes == b.twin_cell_sizes == (2, 2, 2)
    assert a.progress_certified and b.progress_certified


def test_uncertified_rev199_gate_stays_fail_closed():
    edges = {(a, 0) for a in range(5)} | {(5, 1)}
    got = certify_bipartite_twin_split_progress(6, 3, edges, alpha=0.75)
    assert got.status == "bipartite_twin_split_theorem_gate_not_met"
    assert not got.theorem_input_gate
    assert not got.progress_certified


def test_theorem_gate_can_be_stronger_than_configured_recurrence_shrink():
    # Largest twin cell 19/20 = 0.95. With alpha=.96 the rev199 defect gate
    # accepts it, but the rev196 default 0.9 shrink discipline must reject it.
    edges = {(a, 0) for a in range(19)}
    got = certify_bipartite_twin_split_progress(
        20,
        1,
        edges,
        alpha=0.96,
        accounting_shrink_fraction=0.9,
    )
    assert got.theorem_input_gate
    assert got.largest_twin_cell == 19
    assert got.status == "bipartite_twin_split_not_accounting_compatible"
    assert not got.progress_certified


def test_certified_twin_split_composes_with_rev196_accounting():
    edges = {(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2)}
    cert = certify_bipartite_twin_split_progress(6, 3, edges, alpha=0.75)
    children = tuple(_terminal(6, 2) for _ in range(3))
    root = make_twin_split_accounting_node(cert, children, ambient_n=6)
    got = validate_structural_quasipoly_recurrence_tree(root, shrink_fraction=0.9)
    assert got.status == "certified_structural_quasipolynomial_recurrence"
    assert got.certified
    assert got.nodes_checked == 4


def test_accounting_adapter_rejects_children_not_matching_exact_cells():
    edges = {(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2)}
    cert = certify_bipartite_twin_split_progress(6, 3, edges, alpha=0.75)
    with pytest.raises(ValueError, match="match exact twin-cell sizes"):
        make_twin_split_accounting_node(
            cert,
            (_terminal(6, 2), _terminal(6, 4)),
            ambient_n=6,
        )
