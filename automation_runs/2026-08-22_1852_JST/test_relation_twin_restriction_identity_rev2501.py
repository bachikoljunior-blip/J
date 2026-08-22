from __future__ import annotations

from dataclasses import replace
import math

import pytest

from relation_twin_restriction_identity_v1 import (
    certify_relation_twin_restriction_replay_identity,
    validate_relation_twin_restriction_replay_identity,
)


def _edges_from_hyperedges(hyperedges):
    return tuple((a, b) for a, edge in enumerate(hyperedges) for b in edge)


def _relabel_hypergraph(hyperedges, left_perm, right_perm):
    mapped = [tuple(sorted(right_perm[b] for b in edge)) for edge in hyperedges]
    out = [None] * len(mapped)
    for old, new in enumerate(left_perm):
        out[new] = mapped[old]
    return out


def test_positive_exact_restriction_gets_replay_identity():
    edges = _edges_from_hyperedges([(0,), (1,), (2,)])
    got = certify_relation_twin_restriction_replay_identity(3, 7, edges, edges)
    assert got.status == "certified_relation_twin_restriction_replay_identity"
    assert got.identity is not None
    assert got.validation is not None and got.validation.certified
    assert got.result.source.large_twin_class == (3, 4, 5, 6)
    assert got.result.source.selected_part == (0, 1, 2)
    assert len(got.identity.payload_digest) == 64


def test_relabelled_exact_restriction_replays():
    hyperedges = [(0,), (1,), (2,)]
    source = _edges_from_hyperedges(hyperedges)
    target = _edges_from_hyperedges(
        _relabel_hypergraph(
            hyperedges,
            (2, 0, 1),
            (6, 5, 4, 3, 2, 1, 0),
        )
    )
    got = certify_relation_twin_restriction_replay_identity(3, 7, source, target)
    assert got.status == "certified_relation_twin_restriction_replay_identity"
    assert got.result.restriction_pair_complete
    assert got.result.selected_large_class_size == 4


def test_edge_order_and_duplicates_have_one_identity():
    edges = list(_edges_from_hyperedges([(0,), (1,), (2,)]))
    noisy = tuple(reversed(edges)) + (edges[0], edges[1], edges[0])
    clean = tuple(edges)
    a = certify_relation_twin_restriction_replay_identity(3, 7, clean, clean)
    b = certify_relation_twin_restriction_replay_identity(3, 7, noisy, noisy)
    assert a.identity == b.identity


def test_digest_tamper_fails_closed():
    edges = _edges_from_hyperedges([(0,), (1,), (2,)])
    got = certify_relation_twin_restriction_replay_identity(3, 7, edges, edges)
    tampered = replace(got.identity, payload_digest="0" * 64)
    checked = validate_relation_twin_restriction_replay_identity(
        3, 7, edges, edges, got.result, tampered
    )
    assert checked.status == "relation_twin_replay_digest_mismatch"
    assert not checked.certified


def test_input_drift_fails_closed_before_replay_reuse():
    edges = _edges_from_hyperedges([(0,), (1,), (2,)])
    got = certify_relation_twin_restriction_replay_identity(3, 7, edges, edges)
    changed = edges + ((0, 6),)
    checked = validate_relation_twin_restriction_replay_identity(
        3, 7, changed, edges, got.result, got.identity
    )
    assert checked.status == "relation_twin_replay_input_or_resource_drift"
    assert not checked.certified


def test_resource_drift_fails_closed():
    edges = _edges_from_hyperedges([(0,), (1,), (2,)])
    got = certify_relation_twin_restriction_replay_identity(
        3, 7, edges, edges, max_subsets=1000
    )
    checked = validate_relation_twin_restriction_replay_identity(
        3, 7, edges, edges, got.result, got.identity, max_subsets=1001
    )
    assert checked.status == "relation_twin_replay_input_or_resource_drift"
    assert not checked.certified


def test_no_large_twin_class_remains_fail_closed_without_identity():
    cycle = _edges_from_hyperedges([(0, 1), (1, 2), (2, 3), (0, 3)])
    got = certify_relation_twin_restriction_replay_identity(4, 4, cycle, cycle)
    assert got.status == "underlying_relation_twin_restriction_not_complete"
    assert got.identity is None
    assert got.result.source.status == "relation_twin_no_large_class"


def test_inventory_mismatch_remains_fail_closed_without_identity():
    cycle = _edges_from_hyperedges([(0, 1), (1, 2), (2, 3), (0, 3)])
    triangle_tail = _edges_from_hyperedges([(0, 1), (1, 2), (0, 2), (2, 3)])
    got = certify_relation_twin_restriction_replay_identity(
        4, 4, cycle, triangle_tail
    )
    assert got.status == "underlying_relation_twin_restriction_not_complete"
    assert got.identity is None
    assert not got.result.restriction_pair_complete


def test_strict_edge_endpoint_validation_rejects_bool_and_out_of_range():
    edges = _edges_from_hyperedges([(0,), (1,), (2,)])
    with pytest.raises(ValueError):
        certify_relation_twin_restriction_replay_identity(
            3, 7, edges + ((True, 3),), edges
        )
    with pytest.raises(ValueError):
        certify_relation_twin_restriction_replay_identity(
            3, 7, edges + ((0, 7),), edges
        )


def test_invalid_resource_inputs_fail_before_underlying_execution():
    edges = _edges_from_hyperedges([(0,), (1,), (2,)])
    for alpha in (math.nan, math.inf, 0.5, 1.0):
        with pytest.raises(ValueError):
            certify_relation_twin_restriction_replay_identity(
                3, 7, edges, edges, alpha=alpha
            )
    for max_subsets in (True, 0, 1.5):
        with pytest.raises(ValueError):
            certify_relation_twin_restriction_replay_identity(
                3, 7, edges, edges, max_subsets=max_subsets
            )
