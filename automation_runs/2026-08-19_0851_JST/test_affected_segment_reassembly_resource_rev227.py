from __future__ import annotations

import quotient_factored_partial_string_intersection_v1 as _quotient
from affected_segment_reassembly_resource_v1 import (
    affected_segment_reassembly_resource_envelope,
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


def test_reassembly_cap_rejects_before_quotient_preparation(monkeypatch):
    group, blocks = _s5_with_independent_c2_orbit()
    giant = analyze_giant_block_action(group, blocks)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("quotient execution must not start beyond reassembly cap")

    monkeypatch.setattr(_quotient, "prepare_block_action_preimage", forbidden)
    got = quotient_factored_partial_string_intersection(
        group, blocks, (0,) * group.degree, tuple(range(5)),
        max_quotient_leaves=1000,
        giant_certificate=giant,
        max_quotient_schreier_work=10**100,
        max_reassembly_schreier_work=1,
    )
    assert got.status == "undetermined_reassembly_schreier_work_cap"
    assert got.quotient_nodes == got.quotient_leaves == 0
    assert got.reassembly_resource_envelope is not None
    assert not got.reassembly_resource_envelope.admitted


def test_exact_reassembly_charge_is_execution_linked_and_bounded():
    group, blocks = _s5_with_independent_c2_orbit()
    giant = analyze_giant_block_action(group, blocks)
    got = quotient_factored_partial_string_intersection(
        group, blocks, (0, 0, 1, 1, 2, 8, 9), tuple(range(5)),
        max_quotient_leaves=1000,
        max_child_nodes=200000,
        giant_certificate=giant,
        max_quotient_schreier_work=10**100,
        max_reassembly_schreier_work=10**100,
    )
    assert got.status == "exact_quotient_factored_partial_string_intersection"
    charge = got.reassembly_execution_charge
    envelope = got.reassembly_resource_envelope
    assert charge is not None and envelope is not None and charge.envelope_verified
    assert 0 < charge.internal_nodes <= envelope.internal_node_upper_bound
    assert 0 < charge.generator_inputs <= envelope.generator_input_upper_bound
    assert charge.containment_sifts <= envelope.containment_sift_upper_bound
    assert charge.generator_inputs == charge.containment_sifts


def test_reassembly_envelope_counts_all_internal_nodes_and_saturates():
    group, _ = _s5_with_independent_c2_orbit()
    small = affected_segment_reassembly_resource_envelope(group, 5, 120, 601, 1000)
    large = affected_segment_reassembly_resource_envelope(group, 5, 120, 601, 10**100)
    assert small.work_upper_bound == 1001 and not small.admitted
    assert large.internal_node_upper_bound == 481
    assert large.generator_input_upper_bound == 481 * 5 * (group.order + 1)
    assert large.containment_sift_upper_bound == large.generator_input_upper_bound
    assert large.admitted


def test_reused_multiplicity_is_not_saturated_by_an_earlier_work_cap():
    group, _ = _s5_with_independent_c2_orbit()
    huge_leaves = 10**310
    envelope = affected_segment_reassembly_resource_envelope(
        group, 5, huge_leaves, 1 + 5 * huge_leaves, 1,
    )
    assert envelope.internal_node_upper_bound == 1 + 4 * huge_leaves
    assert not envelope.admitted and envelope.work_upper_bound == 2
