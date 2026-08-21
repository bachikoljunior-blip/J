from __future__ import annotations

from types import SimpleNamespace

import pytest

import resource_bounded_imprimitive_candidate_si_v1 as _resource_solver
import s1_string_isomorphism_v4 as _s1
import u2_candidate_coset_string_iso_v8 as _u8
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from s1_proof_identity_v1 import build_s1_proof_identity


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


def large_unique_imprimitive_group(block_count=3, block_size=11):
    return schreier_stabilizer_chain(
        (
            block_cycle(block_count, block_size),
            within_first_block_cycle(block_count, block_size),
        )
    )


def _disable_preclassification_terminals(monkeypatch):
    unresolved = SimpleNamespace(exact=False)
    monkeypatch.setattr(
        _s1,
        "exact_small_order_group_string_isomorphism",
        lambda *_args, **_kwargs: unresolved,
    )
    monkeypatch.setattr(
        _s1,
        "r1_string_isomorphism_child",
        lambda *_args, **_kwargs: unresolved,
    )
    monkeypatch.setattr(
        _s1,
        "exact_if_entire_candidate_maps_string",
        lambda *_args, **_kwargs: unresolved,
    )
    monkeypatch.setattr(
        _s1,
        "exact_literal_giant_string_isomorphism",
        lambda *_args, **_kwargs: unresolved,
    )


def _fake_unresolved_proof(*, root_n, degree, status="undetermined_rev247_test"):
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, degree),
        operation_kind="rev247_test",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=(),
        terminal_certified=False,
        reason="rev247 delegation sentinel",
    )
    return ProofCarryingCoset(
        status,
        None,
        "rev247_test",
        root_n,
        degree,
        True,
        False,
        False,
        0.0,
        False,
        (),
        accounting,
        0,
        "rev247 delegation sentinel",
    )


def test_default_zero_budget_preserves_exact_v7_delegation(monkeypatch):
    _disable_preclassification_terminals(monkeypatch)
    group = large_unique_imprimitive_group()
    calls = []

    def delegated(candidate, source, target, **kwargs):
        calls.append((candidate, source, target, kwargs))
        return _fake_unresolved_proof(root_n=64, degree=group.degree)

    monkeypatch.setattr(_u8, "_delegate_v7", delegated)
    got = _s1.s1_string_isomorphism_v4(
        group,
        (0,) * group.degree,
        (0,) * group.degree,
        root_n=64,
        max_group_order=16,
    )

    assert not got.exact
    assert len(calls) == 1
    assert got.proof_identity is not None
    resources = dict(got.proof_identity.resource_identity)
    assert resources["max_imprimitive_quotient_kernel_work"] == 0
    assert got.proof_identity.dispatcher_identity[1] == (
        "candidate_coset_string_isomorphism_u8"
    )


def test_positive_budget_promotes_rev244_unique_imprimitive_operator(monkeypatch):
    _disable_preclassification_terminals(monkeypatch)
    group = large_unique_imprimitive_group()

    got = _s1.s1_string_isomorphism_v4(
        group,
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
    assert got.resource_envelope is not None
    assert got.resource_envelope.admitted and got.resource_envelope.complete
    assert got.quotient_image_order == 3
    resources = dict(got.proof_identity.resource_identity)
    assert resources["max_imprimitive_quotient_kernel_work"] == 10**40


def test_rejected_shared_s1_budget_fails_before_block_preparation(monkeypatch):
    _disable_preclassification_terminals(monkeypatch)
    group = large_unique_imprimitive_group()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("block preparation started before rev247 admission")

    monkeypatch.setattr(
        _resource_solver,
        "prepare_block_action_preimage",
        forbidden,
    )
    got = _s1.s1_string_isomorphism_v4(
        group,
        (0,) * group.degree,
        (0,) * group.degree,
        root_n=64,
        max_group_order=16,
        max_imprimitive_quotient_kernel_work=1,
    )

    assert not got.exact and got.coset is None
    assert "imprimitive_quotient_kernel_work_cap_exceeded" in got.status
    assert got.resource_envelope is not None
    assert not got.resource_envelope.admitted


def test_imprimitive_budget_is_part_of_replay_identity():
    group = schreier_stabilizer_chain((identity(2),))
    common = dict(
        root_n=2,
        recursion_depth=0,
        polylog_power=2,
        max_explicit_degree=8,
        group_order_poly_power=2,
        max_group_order=1,
        max_partition_states=4,
        max_recognition_nodes=8,
        max_depth=3,
    )
    zero = build_s1_proof_identity(
        group,
        (0, 1),
        (1, 0),
        **common,
    )
    admitted = build_s1_proof_identity(
        group,
        (0, 1),
        (1, 0),
        max_imprimitive_quotient_kernel_work=12345,
        **common,
    )

    assert zero != admitted
    assert dict(zero.resource_identity)["max_imprimitive_quotient_kernel_work"] == 0
    assert (
        dict(admitted.resource_identity)["max_imprimitive_quotient_kernel_work"]
        == 12345
    )


def test_negative_imprimitive_budget_is_rejected():
    group = schreier_stabilizer_chain((identity(2),))
    with pytest.raises(ValueError, match="nonnegative"):
        _s1.s1_string_isomorphism_v4(
            group,
            (0, 1),
            (1, 0),
            root_n=2,
            max_imprimitive_quotient_kernel_work=-1,
        )
