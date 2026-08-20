from __future__ import annotations

from dataclasses import replace
from math import log2

from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from proof_dag_accounting_v1 import validate_execution_proof_dag
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from s1_string_isomorphism_v4 import s1_string_isomorphism_v4


def _terminal(*, root_n=2):
    group = schreier_stabilizer_chain((identity(1),))
    return s1_string_isomorphism_v4(
        group, ("x",), ("x",), root_n=root_n, max_group_order=1
    )


def _shared_parent(first, second, *, parent_m=2, second_multiplicity=1):
    local = 12.0
    accounting = RecurrenceAccountingNode(
        n=first.root_n,
        m=parent_m,
        operation_kind="orbit_partition",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local,
        children=(
            AccountingChild(first.accounting),
            AccountingChild(second.accounting, multiplicity=second_multiplicity),
        ),
        terminal_certified=False,
        reason="two occurrence edges intentionally share one stored identity",
    )
    group = schreier_stabilizer_chain((identity(parent_m),))
    values = tuple(range(parent_m))
    root_identity = s1_string_isomorphism_v4(
        group, values, values, root_n=first.root_n, max_group_order=1
    ).proof_identity
    return ProofCarryingCoset(
        "exact_test_shared_parent",
        None,
        "orbit_partition",
        first.root_n,
        parent_m,
        True,
        True,
        True,
        local,
        False,
        (first, second),
        accounting,
        first.permutation_candidates_checked + second.permutation_candidates_checked,
        "test-only exact shared proof parent",
        root_identity,
    )


def test_shared_storage_identity_is_charged_once_per_execution_edge():
    child = _terminal()
    parent = _shared_parent(child, child)
    check = validate_execution_proof_dag(parent, original_root_n=2)
    assert check.certified, check
    assert check.unique_nodes == 2
    assert check.execution_occurrences == 3
    assert check.reused_occurrences == 1
    expected = 12.0 + child.accounting.local_log2_cost_bound + log2(2)
    assert abs(check.log2_work_bound - expected) < 1e-9


def test_edge_multiplicity_charges_all_represented_occurrences():
    child = _terminal(root_n=4)
    parent = _shared_parent(
        child, child, parent_m=4, second_multiplicity=3
    )
    check = validate_execution_proof_dag(parent, original_root_n=4)
    assert check.certified, check
    assert check.unique_nodes == 2
    assert check.execution_occurrences == 5  # root + 1 + 3 child executions
    assert check.reused_occurrences == 3
    expected = 12.0 + child.accounting.local_log2_cost_bound + log2(4)
    assert abs(check.log2_work_bound - expected) < 1e-9


def test_same_identity_with_different_payload_fails_collision_check():
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
    parent = _shared_parent(child, changed)
    check = validate_execution_proof_dag(parent, original_root_n=2)
    assert not check.certified
    assert check.status == "proof_identity_payload_collision"


def test_missing_root_identity_and_invalid_polynomial_lift_fail_closed():
    child = _terminal()
    missing = replace(child, proof_identity=None)
    assert validate_execution_proof_dag(missing, original_root_n=2).status == "missing_root_proof_identity"

    # The execution root is 2; translating it to original root 1 needs explicit
    # polynomial degree 2.  A different declaration is rejected.
    bad_lift = validate_execution_proof_dag(
        child,
        original_root_n=1,
        polynomial_lift_degree=3,
    )
    assert not bad_lift.certified
    assert bad_lift.status == "invalid_polynomial_root_lift"
