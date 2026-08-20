from paired_bipartite_right_relation_design_bridge_v1 import (
    certify_paired_bipartite_right_relation_design_bridge,
)


def _cycle_incidence():
    return {
        (0, 0), (1, 0),
        (1, 1), (2, 1),
        (2, 2), (3, 2),
        (3, 3), (0, 3),
    }


def _relabel(edges, left_perm, right_perm):
    return {(left_perm[a], right_perm[b]) for a, b in edges}


def test_cycle_relation_reaches_complete_exact_twl_design_branch_plan():
    source = _cycle_incidence()
    target = _relabel(source, (2, 0, 3, 1), (1, 3, 0, 2))
    got = certify_paired_bipartite_right_relation_design_bridge(4, 4, source, target)
    assert got.status == "certified_paired_right_relation_design_branch_plan"
    assert got.selected_arity == 2
    assert got.theorem_hypotheses_certified
    assert got.structural_branch_complete
    assert got.exact and not got.exact_empty
    assert got.branch_plan is not None
    assert got.branch_plan.status == "certified_complete_design_branch_plan"


def test_exact_relation_inventory_mismatch_short_circuits_to_empty():
    source = _cycle_incidence()
    target = {
        (0, 0), (1, 0),
        (0, 1), (1, 1),
        (2, 2), (3, 2),
        (2, 3), (3, 3),
    }
    got = certify_paired_bipartite_right_relation_design_bridge(4, 4, source, target)
    assert got.status == "exact_empty_right_relation_invariant"
    assert got.exact_empty and got.exact and got.structural_branch_complete
    assert got.branch_plan is None


def test_homogeneous_relation_fails_closed_before_design_plan():
    complete = {(a, b) for a in range(4) for b in range(4)}
    got = certify_paired_bipartite_right_relation_design_bridge(4, 4, complete, complete)
    assert got.status == "undetermined_right_relation_design_bridge"
    assert not got.exact and not got.structural_branch_complete
    assert got.branch_plan is None


def test_exact_twl_resource_gate_fails_closed_after_relation_provenance():
    source = _cycle_incidence()
    got = certify_paired_bipartite_right_relation_design_bridge(
        4,
        4,
        source,
        source,
        max_tuple_states=1,
    )
    assert got.status == "undetermined_right_relation_design_branch_plan"
    assert got.relation_provenance.status == "paired_higher_arity_right_relation_provenance"
    assert got.branch_plan is not None
    assert not got.exact and not got.structural_branch_complete
