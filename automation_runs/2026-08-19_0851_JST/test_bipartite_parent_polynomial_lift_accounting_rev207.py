from __future__ import annotations

from bipartite_parent_polynomial_lift_accounting_v2 import (
    solve_and_certify_design_parent_polynomial_lift,
)
import bipartite_parent_polynomial_lift_accounting_v2 as _entry
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _cycle11_edges():
    neighborhoods = [(i, (i + 1) % 11) for i in range(11)]
    return {(a, b) for a, S in enumerate(neighborhoods) for b in S}


def _diagonal_cycle11_parent():
    parent_cycle = tuple((i + 1) % 11 for i in range(11)) + tuple(11 + ((i + 1) % 11) for i in range(11))
    group = schreier_stabilizer_chain([parent_cycle])
    right_index = {11 + i: i for i in range(11)}
    right_images = tuple(
        tuple(right_index[g[11 + i]] for i in range(11))
        for g in group.original_generators
    )
    return group, right_images, parent_cycle


def _solve_cycle11(parent, right_images, edges, **kwargs):
    return solve_and_certify_design_parent_polynomial_lift(
        parent,
        right_images,
        tuple(range(11)),
        tuple(range(11, 22)),
        edges,
        edges,
        root_n=22,
        alpha=0.75,
        max_tuple_states=200,
        max_twl_rounds=32,
        max_twl_work_units=10_000_000,
        max_branch_pairs=200,
        max_auxiliary_degree=160,
        max_image_group_order=16,
        **kwargs,
    )


def test_cycle11_exact_parent_union_gets_polynomial_lift_complexity_certificate():
    parent, right_images, parent_cycle = _diagonal_cycle11_parent()
    edges = _cycle11_edges()
    union, cert = _solve_cycle11(parent, right_images, edges)
    assert union.status == "exact_design_parent_full_string_union_coset"
    assert union.coset is not None and union.coset.contains(parent_cycle)
    assert cert.status == "certified_exact_parent_polynomial_auxiliary_lift"
    assert cert.certified and cert.exact_parent_union and cert.polynomial_auxiliary_gate
    assert cert.structural_branches == cert.exact_branches == 1
    assert cert.branch_certificates[0].accounting_certified
    assert cert.branch_certificates[0].proof_dag_status == "certified_execution_proof_dag"
    assert cert.branch_certificates[0].proof_dag_unique_nodes >= 1
    assert cert.branch_certificates[0].proof_dag_execution_occurrences >= cert.branch_certificates[0].proof_dag_unique_nodes
    assert cert.branch_certificates[0].auxiliary_degree == 143
    assert cert.branch_certificates[0].auxiliary_degree <= cert.auxiliary_degree_bound
    assert cert.total_log2_work_bound <= cert.allowed_log2_work
    captured = union.branch_results[0].image_candidate_proof
    assert captured is not None and captured.exact
    assert captured.status == union.branch_results[0].image_candidate_status


def test_polynomial_lift_consumes_execution_linked_proof_without_replay(monkeypatch):
    parent, right_images, _ = _diagonal_cycle11_parent()
    edges = _cycle11_edges()
    original = _entry.candidate_coset_string_isomorphism_u7
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(_entry, "candidate_coset_string_isomorphism_u7", counted)
    union, cert = _solve_cycle11(parent, right_images, edges)
    assert union.exact
    assert union.branch_results[0].image_candidate_proof is not None
    assert cert.certified
    assert calls == 1


def test_distinct_left_colors_keep_exact_identity_and_certified_lift():
    parent, right_images, parent_cycle = _diagonal_cycle11_parent()
    edges = _cycle11_edges()
    distinct = tuple(range(11))
    union, cert = _solve_cycle11(
        parent,
        right_images,
        edges,
        source_left_colors=distinct,
        target_left_colors=distinct,
    )
    assert union.coset is not None
    assert union.coset.subgroup.order == 1
    assert union.coset.contains(identity(22))
    assert not union.coset.contains(parent_cycle)
    assert cert.certified


def test_unresolved_rev206_image_child_remains_fail_closed_before_cost_claim():
    parent, right_images, _ = _diagonal_cycle11_parent()
    edges = _cycle11_edges()
    union, cert = solve_and_certify_design_parent_polynomial_lift(
        parent,
        right_images,
        tuple(range(11)),
        tuple(range(11, 22)),
        edges,
        edges,
        root_n=22,
        alpha=0.75,
        max_tuple_states=200,
        max_twl_rounds=32,
        max_twl_work_units=10_000_000,
        max_branch_pairs=200,
        max_auxiliary_degree=142,
        max_image_group_order=16,
    )
    assert not union.exact
    assert cert.status == "undetermined_parent_union_not_exact"
    assert not cert.certified
    assert not cert.exact_parent_union


def test_complete_cycle11_cover_with_left_color_inventory_mismatch_is_exact_empty_and_certified():
    parent, right_images, _ = _diagonal_cycle11_parent()
    edges = _cycle11_edges()
    union, cert = _solve_cycle11(
        parent,
        right_images,
        edges,
        source_left_colors=tuple(range(11)),
        target_left_colors=tuple(range(10)) + (9,),
    )
    assert union.exact and union.exact_empty
    assert cert.certified
    assert cert.exact_parent_union


def test_one_shot_iterables_survive_union_then_accounting_replay():
    parent, right_images, parent_cycle = _diagonal_cycle11_parent()
    edges = _cycle11_edges()
    union, cert = solve_and_certify_design_parent_polynomial_lift(
        parent,
        (q for q in right_images),
        (x for x in range(11)),
        (x for x in range(11, 22)),
        ((a, b) for a, b in edges),
        ((a, b) for a, b in edges),
        root_n=22,
        alpha=0.75,
        max_tuple_states=200,
        max_twl_rounds=32,
        max_twl_work_units=10_000_000,
        max_branch_pairs=200,
        max_auxiliary_degree=160,
        max_image_group_order=16,
    )
    assert union.coset is not None and union.coset.contains(parent_cycle)
    assert cert.certified
    assert cert.branch_certificates[0].accounting_certified
