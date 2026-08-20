from itertools import combinations, permutations

from uniform_relation_twin_restriction_v1 import (
    certify_paired_uniform_relation_twin_restriction,
)


def _edges_from_hyperedges(hyperedges):
    return {(a, b) for a, edge in enumerate(hyperedges) for b in edge}


def _ordinary_pair_family():
    return list(combinations(range(4), 2))  # right ground has an extra special point 4


def _relabel_hyperedges(hyperedges, right_perm, left_perm):
    mapped = [tuple(sorted(right_perm[b] for b in edge)) for edge in hyperedges]
    out = [None] * len(mapped)
    for old, new in enumerate(left_perm):
        out[new] = mapped[old]
    return out


def test_large_relation_twin_class_yields_exact_paired_proper_restriction_under_all_right_relabelings():
    source_hyperedges = _ordinary_pair_family()
    source_edges = _edges_from_hyperedges(source_hyperedges)
    left_perm = tuple(reversed(range(6)))
    for right_perm in permutations(range(5)):
        target = _relabel_hyperedges(source_hyperedges, right_perm, left_perm)
        got = certify_paired_uniform_relation_twin_restriction(
            6,
            5,
            source_edges,
            _edges_from_hyperedges(target),
            relation_alpha=0.75,
            restriction_alpha=0.8,
        )
        assert got.status == "certified_paired_uniform_relation_twin_restriction"
        assert got.dominant_twin_size == 4
        assert got.selected_part_index == 0
        assert got.selected_part_size == 4
        assert got.relation_twin_provenance_verified
        assert got.restriction_pair_complete
        assert got.exact and not got.exact_empty
        assert not got.source_symmetry.design_gate_certified
        assert got.source_restriction.selected_alpha_shrink
        assert got.target_restriction.selected_alpha_shrink


def test_relation_design_gate_success_redirects_to_wl_design_child():
    cycle = [(0, 1), (1, 2), (2, 3), (0, 3)]
    edges = _edges_from_hyperedges(cycle)
    got = certify_paired_uniform_relation_twin_restriction(
        4, 4, edges, edges, relation_alpha=0.75
    )
    assert got.status == "relation_design_gate_available"
    assert got.relation_twin_provenance_verified
    assert got.source_symmetry.design_gate_certified
    assert not got.restriction_pair_complete


def test_explicit_johnson_outcome_bypasses_relation_twin_leaf():
    complete = list(combinations(range(4), 2))
    edges = _edges_from_hyperedges(complete)
    got = certify_paired_uniform_relation_twin_restriction(6, 4, edges, edges)
    assert got.status == "explicit_johnson_transport_required"
    assert got.provenance.paired_outcome == "johnson"
    assert got.relation_twin_provenance_verified
    assert not got.restriction_pair_complete


def test_uniform_outcome_mismatch_is_exact_empty():
    source = _ordinary_pair_family()
    target = list(source)
    target[-1] = target[0]  # duplicate neighborhood destroys rev202 twin-free premise
    got = certify_paired_uniform_relation_twin_restriction(
        6, 5, _edges_from_hyperedges(source), _edges_from_hyperedges(target)
    )
    assert got.status == "exact_empty_uniform_relation_invariant"
    assert got.exact_empty and got.exact


def test_proper_restriction_records_one_vertex_descent_without_faking_alpha_shrink():
    source = _ordinary_pair_family()
    edges = _edges_from_hyperedges(source)
    got = certify_paired_uniform_relation_twin_restriction(
        6, 5, edges, edges, relation_alpha=0.75, restriction_alpha=0.75
    )
    assert got.status == "certified_paired_uniform_relation_twin_restriction"
    assert got.selected_part_size == 4
    assert not got.source_restriction.selected_alpha_shrink
    assert not got.target_restriction.selected_alpha_shrink
