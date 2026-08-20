from __future__ import annotations

from itertools import permutations

from relation_wl_design_provenance_v1 import certify_relation_wl_design_provenance


def _edges_from_hyperedges(hyperedges):
    return {(a, b) for a, edge in enumerate(hyperedges) for b in edge}


def _relabel_hypergraph(hyperedges, left_perm, right_perm):
    mapped = [tuple(sorted(right_perm[b] for b in edge)) for edge in hyperedges]
    out = [None] * len(mapped)
    for old, new in enumerate(left_perm):
        out[new] = mapped[old]
    return out


def test_cycle_no_large_relation_twins_wires_to_recursive_design_progress():
    cycle = [(0, 1), (1, 2), (2, 3), (0, 3)]
    edges = _edges_from_hyperedges(cycle)
    got = certify_relation_wl_design_provenance(4, 4, edges, edges)
    assert got.parent.source.status == "relation_twin_no_large_class"
    assert got.parent.target.status == "relation_twin_no_large_class"
    assert got.relation_arity == 2
    assert got.status == "certified_relation_twl_design_recursive_progress"
    assert got.provenance_verified
    assert got.recursive_output_complete
    assert not got.downstream_unresolved
    assert not got.exact_empty
    assert got.child_aux_sizes == (2, 2)
    assert got.progress_inventory


def test_cycle_wiring_is_paired_invariant_under_left_and_right_relabeling():
    cycle = [(0, 1), (1, 2), (2, 3), (0, 3)]
    source = _edges_from_hyperedges(cycle)
    right_perms = [
        tuple(range(4)),
        (3, 2, 1, 0),
        (1, 3, 0, 2),
    ]
    for left_perm in permutations(range(4)):
        for right_perm in right_perms:
            target_hyperedges = _relabel_hypergraph(cycle, left_perm, right_perm)
            target = _edges_from_hyperedges(target_hyperedges)
            got = certify_relation_wl_design_provenance(4, 4, source, target)
            assert got.status == "certified_relation_twl_design_recursive_progress"
            assert got.recursive_output_complete
            assert got.provenance_verified
            assert got.child_aux_sizes == (2, 2)


def test_unary_no_large_twin_relation_is_direct_alpha_partition():
    # Two distinct singleton neighborhoods on four right points give containment
    # colors [1,1,0,0]. Unary transposition-twin classes are therefore 2+2.
    hyperedges = [(0,), (1,)]
    edges = _edges_from_hyperedges(hyperedges)
    got = certify_relation_wl_design_provenance(2, 4, edges, edges)
    assert got.parent.source.status == "relation_twin_no_large_class"
    assert got.relation_arity == 1
    assert got.status == "certified_unary_relation_alpha_split_progress"
    assert got.child_aux_sizes == (2, 2)
    assert got.recursive_output_complete
    assert not got.downstream_unresolved
    assert got.provenance_verified


def test_parent_relation_twin_mismatch_is_exact_empty():
    cycle = [(0, 1), (1, 2), (2, 3), (0, 3)]
    triangle_tail = [(0, 1), (1, 2), (0, 2), (2, 3)]
    got = certify_relation_wl_design_provenance(
        4,
        4,
        _edges_from_hyperedges(cycle),
        _edges_from_hyperedges(triangle_tail),
    )
    assert got.status == "exact_empty_parent_relation_twin_invariant"
    assert got.exact_empty
    assert got.recursive_output_complete


def test_large_relation_twin_branch_is_not_misrouted_into_design():
    hyperedges = [(0,), (1,), (2,)]
    edges = _edges_from_hyperedges(hyperedges)
    got = certify_relation_wl_design_provenance(3, 7, edges, edges)
    assert got.status == "relation_large_twin_restriction_branch_already_selected"
    assert got.parent.status == "paired_relation_twin_restriction"
    assert got.recursive_output_complete
    assert got.design_family is None


def test_exact_twl_resource_gate_fails_closed_without_progress_claim():
    cycle = [(0, 1), (1, 2), (2, 3), (0, 3)]
    edges = _edges_from_hyperedges(cycle)
    got = certify_relation_wl_design_provenance(
        4,
        4,
        edges,
        edges,
        max_tuple_states=1,
    )
    assert got.status == "relation_twl_design_gate_or_resource_closed"
    assert got.provenance_verified
    assert not got.recursive_output_complete
    assert got.downstream_unresolved
    assert not got.exact_empty
