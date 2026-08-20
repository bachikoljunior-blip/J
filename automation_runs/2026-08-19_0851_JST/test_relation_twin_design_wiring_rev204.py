from itertools import combinations

from relation_twin_design_wiring_v1 import wire_no_large_twin_relation_into_design


def _edges(hyperedges):
    return {(a, b) for a, edge in enumerate(hyperedges) for b in edge}


def _cycle5():
    return [(i, (i + 1) % 5) for i in range(5)]


def test_cycle5_no_large_twins_reaches_complete_exact_design_branch_plan():
    edges = _edges(_cycle5())
    got = wire_no_large_twin_relation_into_design(
        5, 5, edges, edges,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_work_units=2_000_000,
    )
    assert got.status == "certified_relation_design_branch_plan"
    assert got.relation_arity == 2
    assert got.parent_provenance_verified
    assert got.theorem_hypotheses_certified
    assert got.structural_branch_complete
    assert got.exact and not got.exact_empty
    assert got.branch_plan is not None
    assert got.branch_plan.status == "certified_complete_design_branch_plan"


def test_unary_no_large_twin_relation_is_direct_half_bounded_coloring():
    edges = {(0, 0), (1, 1)}
    got = wire_no_large_twin_relation_into_design(2, 4, edges, edges)
    assert got.status == "certified_unary_relation_half_bounded_coloring"
    assert got.relation_arity == 1
    assert tuple(map(len, got.source_unary_partition)) == (2, 2)
    assert tuple(map(len, got.target_unary_partition)) == (2, 2)
    assert got.parent_provenance_verified and got.structural_branch_complete
    assert got.branch_plan is None


def test_over_half_twin_relation_redirects_to_rev203_restriction():
    ordinary_pairs = list(combinations(range(4), 2))
    edges = _edges(ordinary_pairs)
    got = wire_no_large_twin_relation_into_design(6, 5, edges, edges, alpha=0.8)
    assert got.status == "relation_twin_restriction_available"
    assert got.relation_twin.status == "paired_relation_twin_restriction"
    assert got.structural_branch_complete and got.exact
    assert got.branch_plan is None


def test_explicit_johnson_outcome_is_left_for_ambient_transport():
    complete = list(combinations(range(4), 2))
    edges = _edges(complete)
    got = wire_no_large_twin_relation_into_design(6, 4, edges, edges)
    assert got.status == "explicit_johnson_transport_required"
    assert got.exact and not got.structural_branch_complete


def test_twl_resource_cap_fails_closed_after_mechanical_parent_provenance():
    edges = _edges(_cycle5())
    got = wire_no_large_twin_relation_into_design(
        5, 5, edges, edges, alpha=0.75, max_tuple_states=1
    )
    assert got.status == "undetermined_relation_design_branch_plan"
    assert got.parent_provenance_verified
    assert got.branch_plan is not None
    assert not got.exact and not got.structural_branch_complete


def test_parent_relation_status_mismatch_is_exact_empty():
    source = _edges(_cycle5())
    target_hyperedges = list(_cycle5())
    target_hyperedges[-1] = target_hyperedges[0]
    got = wire_no_large_twin_relation_into_design(5, 5, source, _edges(target_hyperedges))
    assert got.status == "exact_empty_relation_twin_parent_invariant"
    assert got.exact_empty and got.exact
