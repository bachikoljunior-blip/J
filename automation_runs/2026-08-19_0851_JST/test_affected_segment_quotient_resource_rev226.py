from __future__ import annotations

import quotient_factored_partial_string_intersection_v1 as _quotient
from affected_segment_quotient_resource_v1 import (
    affected_segment_quotient_resource_envelope,
)
from giant_block_action_certificates import analyze_giant_block_action
from permutation_group_schreier import schreier_stabilizer_chain
from quotient_factored_partial_string_intersection_v1 import (
    quotient_factored_partial_string_intersection,
)


def _s5_with_independent_c2_orbit():
    n = 7
    e = list(range(n))
    swap = e.copy(); swap[0], swap[1] = 1, 0
    cycle = e.copy()
    for i in range(5):
        cycle[i] = (i + 1) % 5
    extra = e.copy(); extra[5], extra[6] = 6, 5
    return schreier_stabilizer_chain((tuple(swap), tuple(cycle), tuple(extra))), tuple((i,) for i in range(5))


def test_leaf_order_rejects_before_shared_preimage_preparation(monkeypatch):
    group, blocks = _s5_with_independent_c2_orbit()
    giant = analyze_giant_block_action(group, blocks)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("quotient preparation must not start beyond the leaf cap")

    monkeypatch.setattr(_quotient, "prepare_block_action_preimage", forbidden)
    got = quotient_factored_partial_string_intersection(
        group, blocks, (0,) * group.degree, tuple(range(5)),
        max_quotient_leaves=10,
        giant_certificate=giant,
        max_quotient_schreier_work=10**100,
    )
    assert got.status == "undetermined_quotient_leaf_limit"
    assert got.quotient_nodes == got.quotient_leaves == 0
    assert got.resource_envelope is not None and not got.resource_envelope.admitted


def test_work_cap_rejects_before_quotient_recursion(monkeypatch):
    group, blocks = _s5_with_independent_c2_orbit()
    giant = analyze_giant_block_action(group, blocks)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("quotient preparation must not start beyond the work cap")

    monkeypatch.setattr(_quotient, "prepare_block_action_preimage", forbidden)
    got = quotient_factored_partial_string_intersection(
        group, blocks, (0,) * group.degree, tuple(range(5)),
        max_quotient_leaves=1000,
        giant_certificate=giant,
        max_quotient_schreier_work=1,
    )
    assert got.status == "undetermined_quotient_schreier_work_cap"
    assert got.resource_envelope.work_upper_bound == 2


def test_admitted_execution_prepares_block_homomorphism_once(monkeypatch):
    group, blocks = _s5_with_independent_c2_orbit()
    giant = analyze_giant_block_action(group, blocks)
    original = _quotient.prepare_block_action_preimage
    calls = []

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(_quotient, "prepare_block_action_preimage", counted)
    got = quotient_factored_partial_string_intersection(
        group, blocks, (0, 0, 1, 1, 2, 8, 9), tuple(range(5)),
        max_quotient_leaves=1000,
        max_child_nodes=200000,
        giant_certificate=giant,
        max_quotient_schreier_work=10**100,
    )
    assert got.status == "exact_quotient_factored_partial_string_intersection"
    assert got.quotient_leaves == 120 and len(calls) == 1
    assert got.resource_envelope is not None and got.resource_envelope.admitted


def test_envelope_counts_all_leaf_child_node_caps_and_saturates():
    group, _ = _s5_with_independent_c2_orbit()
    small = affected_segment_quotient_resource_envelope(
        group, 5, 120, max_quotient_leaves=1000,
        max_child_nodes=17, max_work=1000,
    )
    large = affected_segment_quotient_resource_envelope(
        group, 5, 120, max_quotient_leaves=1000,
        max_child_nodes=17, max_work=10**100,
    )
    assert small.work_upper_bound == 1001 and not small.admitted
    assert large.quotient_leaf_upper_bound == 120
    assert large.quotient_node_upper_bound == 601
    assert large.kernel_child_upper_bound == 840
    assert large.child_search_node_upper_bound == 15120
    assert large.admitted
