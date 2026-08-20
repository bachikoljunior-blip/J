from __future__ import annotations

from dataclasses import replace

import bipartite_parent_polynomial_lift_accounting_v1 as _core
import bipartite_parent_polynomial_lift_accounting_v2 as _entry
from permutation_group_schreier import schreier_stabilizer_chain


def _cycle5_edges():
    neighborhoods = [(i, (i + 1) % 5) for i in range(5)]
    return {(a, b) for a, pair in enumerate(neighborhoods) for b in pair}


def _instance():
    cycle = tuple((i + 1) % 5 for i in range(5)) + tuple(
        5 + ((i + 1) % 5) for i in range(5)
    )
    parent = schreier_stabilizer_chain([cycle])
    right_index = {5 + i: i for i in range(5)}
    images = tuple(
        tuple(right_index[g[5 + i]] for i in range(5))
        for g in parent.original_generators
    )
    return parent, images, _cycle5_edges()


def _solve(parent, images, edges):
    return _entry.solve_and_certify_design_parent_polynomial_lift(
        parent,
        images,
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


def test_rev206_execution_object_is_the_rev207_accounting_object(monkeypatch):
    parent, images, edges = _instance()
    original = _entry.candidate_coset_string_isomorphism_u7
    observed = []

    def observed_execution(*args, **kwargs):
        proof = original(*args, **kwargs)
        observed.append(proof)
        return proof

    monkeypatch.setattr(
        _entry,
        "candidate_coset_string_isomorphism_u7",
        observed_execution,
    )
    union, cert = _solve(parent, images, edges)

    assert cert.certified
    assert len(observed) == 1
    assert len(union.branch_results) == 1
    captured = union.branch_results[0].image_candidate_proof
    assert captured is observed[0]
    assert cert.branch_certificates[0].image_status == captured.status


def test_missing_execution_proof_fails_closed_instead_of_replaying(monkeypatch):
    parent, images, edges = _instance()
    original_union = _core.solve_design_witness_cover_in_parent_bipartite_action

    def drop_execution_proof(*args, **kwargs):
        union = original_union(*args, **kwargs)
        branches = tuple(
            replace(branch, image_candidate_proof=None)
            for branch in union.branch_results
        )
        return replace(union, branch_results=branches)

    monkeypatch.setattr(
        _core,
        "solve_design_witness_cover_in_parent_bipartite_action",
        drop_execution_proof,
    )
    union, cert = _solve(parent, images, edges)

    assert union.exact
    assert not cert.certified
    assert cert.status == "undetermined_uncertified_candidate_image_accounting"
    assert not cert.branch_certificates[0].exact
    assert cert.branch_certificates[0].image_status is None

