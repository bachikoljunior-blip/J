from __future__ import annotations

from dataclasses import replace
from math import log2

from design_child_proof_dag_cover_v1 import validate_design_child_proof_dag_cover
from design_full_string_child_resource_proof_v1 import (
    certify_design_full_string_child_resources,
)
from design_tuple_full_string_union_si_v1 import DesignTupleFullStringSI
from permutation_group_schreier import identity, schreier_stabilizer_chain
from s1_string_isomorphism_v4 import s1_string_isomorphism_v4


def _terminal(*, root_n: int = 2):
    group = schreier_stabilizer_chain((identity(1),))
    child = s1_string_isomorphism_v4(
        group, ("x",), ("x",), root_n=root_n, max_group_order=1
    )
    assert child.exact and child.local_cost_certified
    assert child.proof_identity is not None
    return child


def _design_result(children, *, root_n: int = 2, complete: bool = True):
    children = tuple(children)
    resource = certify_design_full_string_child_resources(
        children,
        expected_branch_count=len(children),
        original_root_degree=root_n,
        quasipoly_constant=32768.0,
    )
    assert resource.certified, resource
    return DesignTupleFullStringSI(
        "exact_empty_design_tuple_full_string_union",
        None,
        children,
        len(children),
        0,
        True,
        complete,
        0.0,
        "test-only complete Design child cover",
        resource,
    )


def test_cross_branch_storage_reuse_never_erases_execution_charge():
    child = _terminal()
    result = _design_result((child, child))
    check = validate_design_child_proof_dag_cover(result, original_root_n=2)
    assert check.certified, check
    assert check.status == "certified_design_child_proof_dag_cover"
    assert check.branch_count == 2
    assert check.validated_branch_count == 2
    assert check.unique_nodes == 1
    assert check.execution_occurrences == 2
    assert check.reused_occurrences == 0
    assert check.cross_branch_reused_nodes == 1
    expected = child.accounting.local_log2_cost_bound + log2(2)
    assert abs(check.combined_child_log2_work_bound - expected) < 1e-9


def test_same_identity_with_different_cross_branch_payload_fails_closed():
    child = _terminal()
    changed_accounting = replace(
        child.accounting,
        local_log2_cost_bound=child.accounting.local_log2_cost_bound + 1.0,
    )
    changed = replace(
        child,
        local_log2_cost_bound=child.local_log2_cost_bound + 1.0,
        accounting=changed_accounting,
    )
    result = _design_result((child, changed))
    check = validate_design_child_proof_dag_cover(result, original_root_n=2)
    assert not check.certified
    assert check.status == "cross_branch_proof_identity_payload_collision"
    assert check.failed_branch_index == 1


def test_missing_execution_identity_fails_without_replaying_child_solver():
    child = _terminal()
    missing = replace(child, proof_identity=None)
    result = _design_result((missing,))
    check = validate_design_child_proof_dag_cover(result, original_root_n=2)
    assert not check.certified
    assert check.status == "missing_root_proof_identity"
    assert check.failed_branch_index == 0


def test_independent_tree_and_dag_cover_charges_must_agree():
    child = _terminal()
    result = _design_result((child,))
    bad_resource = replace(
        result.child_resource_proof,
        combined_log2_work_bound=(
            result.child_resource_proof.combined_log2_work_bound + 0.5
        ),
    )
    check = validate_design_child_proof_dag_cover(
        replace(result, child_resource_proof=bad_resource),
        original_root_n=2,
    )
    assert not check.certified
    assert check.status == "design_child_tree_dag_charge_mismatch"


def test_partial_cover_and_recorded_branch_count_mismatch_fail_closed():
    child = _terminal()
    result = _design_result((child,))
    partial = validate_design_child_proof_dag_cover(
        replace(result, complete=False), original_root_n=2
    )
    assert not partial.certified
    assert partial.status == "incomplete_or_nonexact_design_child_cover"

    mismatch = validate_design_child_proof_dag_cover(
        replace(result, branches_checked=2), original_root_n=2
    )
    assert not mismatch.certified
    assert mismatch.status == "design_child_branch_count_mismatch"


def test_external_caller_charge_is_composed_without_hiding_child_work():
    child = _terminal()
    result = _design_result((child,))
    check = validate_design_child_proof_dag_cover(
        result,
        original_root_n=2,
        external_log2_cost_bound=100.0,
        quasipoly_constant=100.0,
    )
    assert not check.certified
    assert check.status == "design_child_proof_dag_envelope_exceeded"
    assert check.total_log2_work_bound > check.allowed_log2_work


def test_exact_zero_child_cover_is_vacuously_certified():
    result = DesignTupleFullStringSI(
        "exact_empty_design_tuple_transport",
        None,
        (),
        0,
        0,
        True,
        True,
        1.0,
        "the complete upstream cover is empty",
    )
    check = validate_design_child_proof_dag_cover(
        result,
        original_root_n=2,
        external_log2_cost_bound=1.0,
        quasipoly_constant=100.0,
    )
    assert check.certified, check
    assert check.status == "certified_empty_design_child_proof_dag_cover"
    assert check.branch_count == 0
    assert check.unique_nodes == 0
    assert check.total_log2_work_bound == 1.0
