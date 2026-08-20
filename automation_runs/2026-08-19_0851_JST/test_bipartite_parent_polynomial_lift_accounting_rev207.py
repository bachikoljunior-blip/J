from __future__ import annotations

from bipartite_parent_polynomial_lift_accounting_v1 import (
    solve_and_certify_design_parent_polynomial_lift,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _cycle5_edges():
    neighborhoods = [(i, (i + 1) % 5) for i in range(5)]
    return {(a, b) for a, S in enumerate(neighborhoods) for b in S}


def _diagonal_cycle5_parent():
    parent_cycle = tuple((i + 1) % 5 for i in range(5)) + tuple(5 + ((i + 1) % 5) for i in range(5))
    group = schreier_stabilizer_chain([parent_cycle])
    right_index = {5 + i: i for i in range(5)}
    right_images = tuple(
        tuple(right_index[g[5 + i]] for i in range(5))
        for g in group.original_generators
    )
    return group, right_images, parent_cycle


def test_cycle5_exact_parent_union_gets_polynomial_lift_complexity_certificate():
    parent, right_images, parent_cycle = _diagonal_cycle5_parent()
    edges = _cycle5_edges()
    union, cert = solve_and_certify_design_parent_polynomial_lift(
        parent,
        right_images,
        tuple(range(5)),
        tuple(range(5, 10)),
        edges,
        edges,
        root_n=10,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_rounds=16,
        max_twl_work_units=2_000_000,
        max_branch_pairs=100,
        max_auxiliary_degree=40,
        max_image_group_order=16,
    )
    assert union.status == "exact_design_parent_full_string_union_coset"
    assert union.coset is not None and union.coset.contains(parent_cycle)
    # cycle5 stays a typed unresolved structural UPCC in rev206's shrink gate,
    # but the exact candidate SI that rev206 actually executed is independently
    # proof-carrying.  rev207 certifies that exact path under a polynomial lift.
    assert cert.status == "certified_exact_parent_polynomial_auxiliary_lift"
    assert cert.certified and cert.exact_parent_union and cert.polynomial_auxiliary_gate
    assert cert.structural_branches == cert.exact_branches == 1
    assert cert.branch_certificates[0].accounting_certified
    assert cert.branch_certificates[0].auxiliary_degree == 35
    assert cert.branch_certificates[0].auxiliary_degree <= cert.auxiliary_degree_bound
    assert cert.total_log2_work_bound <= cert.allowed_log2_work


def test_distinct_left_colors_keep_exact_identity_and_certified_lift():
    parent, right_images, parent_cycle = _diagonal_cycle5_parent()
    edges = _cycle5_edges()
    distinct = tuple(range(5))
    union, cert = solve_and_certify_design_parent_polynomial_lift(
        parent,
        right_images,
        tuple(range(5)),
        tuple(range(5, 10)),
        edges,
        edges,
        source_left_colors=distinct,
        target_left_colors=distinct,
        root_n=10,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_rounds=16,
        max_twl_work_units=2_000_000,
        max_branch_pairs=100,
        max_auxiliary_degree=40,
        max_image_group_order=16,
    )
    assert union.coset is not None
    assert union.coset.subgroup.order == 1
    assert union.coset.contains(identity(10))
    assert not union.coset.contains(parent_cycle)
    assert cert.certified


def test_unresolved_rev206_image_child_remains_fail_closed_before_cost_claim():
    parent, right_images, _ = _diagonal_cycle5_parent()
    edges = _cycle5_edges()
    union, cert = solve_and_certify_design_parent_polynomial_lift(
        parent,
        right_images,
        tuple(range(5)),
        tuple(range(5, 10)),
        edges,
        edges,
        root_n=10,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_rounds=16,
        max_twl_work_units=2_000_000,
        max_branch_pairs=100,
        max_auxiliary_degree=34,
        max_image_group_order=16,
    )
    assert not union.exact
    assert cert.status == "undetermined_parent_union_not_exact"
    assert not cert.certified
    assert not cert.exact_parent_union


def test_complete_cycle5_cover_with_left_color_inventory_mismatch_is_exact_empty_and_certified():
    parent, right_images, _ = _diagonal_cycle5_parent()
    edges = _cycle5_edges()
    union, cert = solve_and_certify_design_parent_polynomial_lift(
        parent,
        right_images,
        tuple(range(5)),
        tuple(range(5, 10)),
        edges,
        edges,
        source_left_colors=(0, 1, 2, 3, 4),
        target_left_colors=(0, 1, 2, 3, 3),
        root_n=10,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_rounds=16,
        max_twl_work_units=2_000_000,
        max_branch_pairs=100,
        max_auxiliary_degree=40,
        max_image_group_order=16,
    )
    assert union.exact and union.exact_empty
    assert cert.certified
    assert cert.exact_parent_union
