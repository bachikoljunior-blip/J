from itertools import combinations

from uniform_relation_design_bridge_v1 import (
    certify_paired_uniform_relation_design_bridge,
)


def _edges_from_hyperedges(hyperedges):
    return {(a, b) for a, edge in enumerate(hyperedges) for b in edge}


def _cycle5():
    return [(i, (i + 1) % 5) for i in range(5)]


def test_cycle5_actual_containment_relation_reaches_complete_exact_design_plan():
    edges = _edges_from_hyperedges(_cycle5())
    got = certify_paired_uniform_relation_design_bridge(
        5,
        5,
        edges,
        edges,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_work_units=2_000_000,
    )
    assert got.status == "certified_uniform_relation_design_branch_plan"
    assert got.relation_arity == 2
    assert got.theorem_hypotheses_certified
    assert got.structural_branch_complete
    assert got.exact and not got.exact_empty
    assert got.branch_plan is not None
    assert got.branch_plan.status == "certified_complete_design_branch_plan"


def test_unary_containment_relation_is_direct_alpha_partition():
    # Two distinct degree-one neighborhoods on a four-point right ground.
    edges = {(0, 0), (1, 1)}
    got = certify_paired_uniform_relation_design_bridge(2, 4, edges, edges, alpha=0.75)
    assert got.status == "certified_unary_relation_alpha_partition"
    assert got.relation_arity == 1
    assert got.theorem_hypotheses_certified
    assert got.structural_branch_complete
    assert tuple(map(len, got.source_unary_partition)) == (2, 2)
    assert tuple(map(len, got.target_unary_partition)) == (2, 2)
    assert got.branch_plan is None


def test_large_relation_twin_regime_redirects_to_rev203_restriction():
    ordinary_pairs = list(combinations(range(4), 2))
    edges = _edges_from_hyperedges(ordinary_pairs)
    got = certify_paired_uniform_relation_design_bridge(
        6,
        5,
        edges,
        edges,
        alpha=0.75,
        restriction_alpha=0.8,
    )
    assert got.status == "relation_twin_restriction_available"
    assert got.relation_gate.status == "certified_paired_uniform_relation_twin_restriction"
    assert got.structural_branch_complete and got.exact
    assert got.branch_plan is None


def test_explicit_johnson_outcome_is_kept_for_ambient_transport():
    complete = list(combinations(range(4), 2))
    edges = _edges_from_hyperedges(complete)
    got = certify_paired_uniform_relation_design_bridge(6, 4, edges, edges)
    assert got.status == "explicit_johnson_transport_required"
    assert not got.structural_branch_complete
    assert got.exact


def test_exact_twl_resource_cap_fails_closed_after_design_gate():
    edges = _edges_from_hyperedges(_cycle5())
    got = certify_paired_uniform_relation_design_bridge(
        5, 5, edges, edges, alpha=0.75, max_tuple_states=1
    )
    assert got.status == "undetermined_uniform_relation_design_branch_plan"
    assert got.relation_gate.status == "relation_design_gate_available"
    assert got.branch_plan is not None
    assert not got.structural_branch_complete
    assert not got.exact


def test_rev202_outcome_mismatch_propagates_exact_empty():
    source = _edges_from_hyperedges(_cycle5())
    target_hyperedges = list(_cycle5())
    target_hyperedges[-1] = target_hyperedges[0]
    target = _edges_from_hyperedges(target_hyperedges)
    got = certify_paired_uniform_relation_design_bridge(5, 5, source, target)
    assert got.status == "exact_empty_uniform_relation_design_invariant"
    assert got.exact_empty and got.exact
