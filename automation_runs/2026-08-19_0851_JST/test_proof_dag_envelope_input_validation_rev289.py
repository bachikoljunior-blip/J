from __future__ import annotations

import math

import pytest

from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_dag_accounting_v1 import validate_execution_proof_dag
from s1_string_isomorphism_v4 import s1_string_isomorphism_v4


def _terminal(*, root_n=2):
    group = schreier_stabilizer_chain((identity(1),))
    return s1_string_isomorphism_v4(
        group, ("x",), ("x",), root_n=root_n, max_group_order=1
    )


def test_valid_baseline_still_certifies():
    proof = _terminal(root_n=2)
    check = validate_execution_proof_dag(
        proof,
        original_root_n=2,
        external_log2_cost_bound=0.0,
        quasipoly_power=5,
        quasipoly_constant=32768.0,
    )
    assert check.certified, check
    assert check.status == "certified_execution_proof_dag"
    assert math.isfinite(check.log2_work_bound)
    assert math.isfinite(check.allowed_log2_work)


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf"), True, "0", -1.0],
)
def test_external_cost_malformed_values_fail_closed_before_comparison(value):
    proof = _terminal()
    check = validate_execution_proof_dag(
        proof,
        original_root_n=2,
        external_log2_cost_bound=value,
    )
    assert not check.certified
    assert check.status == "invalid_proof_dag_envelope"
    assert math.isfinite(check.log2_work_bound)
    assert math.isfinite(check.allowed_log2_work)


@pytest.mark.parametrize("value", [True, 2.0, "2", 0, -1])
def test_original_root_requires_positive_strict_integer(value):
    proof = _terminal()
    check = validate_execution_proof_dag(proof, original_root_n=value)
    assert not check.certified
    assert check.status == "invalid_proof_dag_envelope"


@pytest.mark.parametrize("value", [True, 5.0, "5", -1])
def test_quasipoly_power_requires_nonnegative_strict_integer(value):
    proof = _terminal()
    check = validate_execution_proof_dag(
        proof,
        original_root_n=2,
        quasipoly_power=value,
    )
    assert not check.certified
    assert check.status == "invalid_proof_dag_envelope"


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf"), True, "32768", -1.0],
)
def test_quasipoly_constant_requires_finite_nonnegative_real(value):
    proof = _terminal()
    check = validate_execution_proof_dag(
        proof,
        original_root_n=2,
        quasipoly_constant=value,
    )
    assert not check.certified
    assert check.status == "invalid_proof_dag_envelope"


@pytest.mark.parametrize("value", [True, 2.0, "2", 0, -1])
def test_explicit_polynomial_lift_requires_positive_strict_integer(value):
    proof = _terminal()
    check = validate_execution_proof_dag(
        proof,
        original_root_n=2,
        polynomial_lift_degree=value,
    )
    assert not check.certified
    assert check.status == "invalid_polynomial_root_lift"


def test_nan_external_cost_regression_cannot_certify():
    proof = _terminal()
    check = validate_execution_proof_dag(
        proof,
        original_root_n=2,
        external_log2_cost_bound=float("nan"),
    )
    assert check.status == "invalid_proof_dag_envelope"
    assert check.certified is False
    assert check.log2_work_bound == 0.0


def test_overflowing_envelope_arithmetic_fails_closed():
    proof = _terminal(root_n=4)
    check = validate_execution_proof_dag(
        proof,
        original_root_n=4,
        quasipoly_power=1024,
        quasipoly_constant=1e308,
    )
    assert not check.certified
    assert check.status == "invalid_proof_dag_envelope"
    assert check.allowed_log2_work == 0.0
