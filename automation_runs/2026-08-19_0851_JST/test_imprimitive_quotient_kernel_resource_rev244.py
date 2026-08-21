import imprimitive_quotient_kernel_resource_v1 as _resource
import resource_bounded_imprimitive_candidate_si_v1 as _solver
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from u2_candidate_coset_string_iso_v8 import (
    candidate_coset_string_isomorphism_u8,
)


def block_cycle(block_count, block_size):
    n = block_count * block_size
    permutation = list(range(n))
    for block in range(block_count):
        for offset in range(block_size):
            permutation[block * block_size + offset] = (
                ((block + 1) % block_count) * block_size + offset
            )
    return tuple(permutation)


def within_first_block_cycle(block_count, block_size):
    n = block_count * block_size
    permutation = list(range(n))
    for offset in range(block_size):
        permutation[offset] = (offset + 1) % block_size
    return tuple(permutation)


def transposition(n, left=0, right=1):
    permutation = list(range(n))
    permutation[left], permutation[right] = (
        permutation[right],
        permutation[left],
    )
    return tuple(permutation)


def large_unique_imprimitive_group(block_count=3, block_size=11):
    return schreier_stabilizer_chain(
        (
            block_cycle(block_count, block_size),
            within_first_block_cycle(block_count, block_size),
        )
    )


def contiguous_blocks(block_count=3, block_size=11):
    return tuple(
        tuple(range(block * block_size, (block + 1) * block_size))
        for block in range(block_count)
    )


def test_cap_rejects_before_prepared_block_homomorphism(monkeypatch):
    group = large_unique_imprimitive_group()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("prepared block homomorphism started before admission")

    monkeypatch.setattr(_solver, "prepare_block_action_preimage", forbidden)
    got = _solver.resource_bounded_imprimitive_string_isomorphism(
        group,
        (0,) * group.degree,
        (0,) * group.degree,
        root_n=64,
        max_quotient_image_order=16,
        max_candidate_group_order=16,
        max_imprimitive_quotient_kernel_work=1,
    )
    assert not got.exact and got.coset is None
    assert got.status == "undetermined_imprimitive_quotient_kernel_work_cap_exceeded"
    assert got.resource_envelope is not None
    assert not got.resource_envelope.admitted
    assert got.resource_envelope.work_upper_bound == 2


def test_envelope_saturates_only_at_caller_cap_plus_one():
    group = large_unique_imprimitive_group()
    envelope = _resource.imprimitive_quotient_kernel_resource_envelope(
        group,
        contiguous_blocks(),
        (0,) * group.degree,
        original_root_degree=64,
        quotient_order_poly_power=2,
        max_quotient_image_order=16,
        candidate_group_order_poly_power=2,
        max_candidate_group_order=16,
        max_work=7,
    )
    assert not envelope.admitted
    assert envelope.work_upper_bound == 8
    assert envelope.child_terminal_kind == "state_orbit"


def test_admitted_execution_prepares_once_and_records_complete_cover(monkeypatch):
    group = large_unique_imprimitive_group()
    calls = {"prepare": 0, "lift": 0}
    original_prepare = _solver.prepare_block_action_preimage
    original_lift = _solver.lift_prepared_block_action_preimage

    def counted_prepare(*args, **kwargs):
        calls["prepare"] += 1
        return original_prepare(*args, **kwargs)

    def counted_lift(*args, **kwargs):
        calls["lift"] += 1
        return original_lift(*args, **kwargs)

    monkeypatch.setattr(_solver, "prepare_block_action_preimage", counted_prepare)
    monkeypatch.setattr(_solver, "lift_prepared_block_action_preimage", counted_lift)

    got = _solver.resource_bounded_imprimitive_string_isomorphism(
        group,
        (0,) * group.degree,
        (0,) * group.degree,
        root_n=64,
        max_quotient_image_order=16,
        max_candidate_group_order=16,
        max_imprimitive_quotient_kernel_work=10**40,
    )
    assert got.exact and got.coset is not None
    assert got.coset.subgroup.order == group.order
    assert got.quotient_image_order == 3
    assert calls == {"prepare": 1, "lift": 3}

    envelope = got.resource_envelope
    assert envelope is not None and envelope.admitted and envelope.complete
    assert envelope.child_terminal_kind == "state_orbit"
    assert envelope.executed_preparation_count == 1
    assert envelope.executed_quotient_order == 3
    assert envelope.executed_fiber_count == 3
    assert envelope.permutation_candidates_checked == 3
    accounting = validate_quasipoly_recurrence_tree_v4(got.accounting)
    assert accounting.certified, accounting


def test_candidate_v8_preserves_nonidentity_right_coset_coordinates():
    group = large_unique_imprimitive_group()
    representative = transposition(group.degree)
    candidate = RightCoset(group, representative)

    got = candidate_coset_string_isomorphism_u8(
        candidate,
        (0,) * group.degree,
        (0,) * group.degree,
        root_n=64,
        max_group_order=16,
        max_imprimitive_quotient_kernel_work=10**40,
    )
    assert got.exact and got.coset is not None
    assert got.status.startswith(
        "exact_translated_exact_resource_bounded_imprimitive_si_coset"
    )
    assert got.coset.subgroup.order == group.order
    assert got.coset.contains(representative)
    assert got.resource_envelope is not None
    assert got.resource_envelope.complete


def test_universal_quotient_gate_rejects_before_execution(monkeypatch):
    group = large_unique_imprimitive_group()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("quotient preparation started despite gate rejection")

    monkeypatch.setattr(_solver, "prepare_block_action_preimage", forbidden)
    got = _solver.resource_bounded_imprimitive_string_isomorphism(
        group,
        (0,) * group.degree,
        (0,) * group.degree,
        root_n=64,
        max_quotient_image_order=2,
        max_candidate_group_order=16,
        max_imprimitive_quotient_kernel_work=10**40,
    )
    assert got.status == (
        "undetermined_imprimitive_quotient_kernel_quotient_gate_unavailable"
    )
    assert not got.exact
    assert got.resource_envelope is not None
    assert not got.resource_envelope.quotient_gate_certified
