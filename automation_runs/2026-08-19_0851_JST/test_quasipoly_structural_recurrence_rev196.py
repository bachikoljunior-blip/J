from math import log2

from quasipoly_structural_recurrence_accounting_v2 import (
    PHASE_CLIQUE,
    PHASE_JOHNSON,
    PHASE_UPCC,
    StructuralAccountingChild,
    StructuralRecurrenceAccountingNode,
    validate_structural_quasipoly_recurrence_tree,
)


def _terminal(n, m, phase, cost=2.0):
    return StructuralRecurrenceAccountingNode(
        n=n,
        m=m,
        structural_phase=phase,
        operation_kind="terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=cost,
        children=(),
        terminal_certified=True,
        reason="exact test terminal",
    )


def test_clique_to_upcc_to_johnson_then_numeric_shrink_is_valid_progress():
    leaf = _terminal(128, 50, PHASE_CLIQUE)
    johnson = StructuralRecurrenceAccountingNode(
        128, 100, PHASE_JOHNSON, "aux_shrink", True, True, 3.0,
        (StructuralAccountingChild(leaf),), False, "Johnson ground shrinks auxiliary measure",
    )
    upcc = StructuralRecurrenceAccountingNode(
        128, 100, PHASE_UPCC, "structural_upgrade", True, True, 3.0,
        (StructuralAccountingChild(johnson),), False, "UPCC canonically becomes Johnson",
    )
    clique = StructuralRecurrenceAccountingNode(
        128, 100, PHASE_CLIQUE, "structural_upgrade", True, True, 3.0,
        (StructuralAccountingChild(upcc),), False, "clique canonically becomes UPCC",
    )
    got = validate_structural_quasipoly_recurrence_tree(clique)
    assert got.status == "certified_structural_quasipolynomial_recurrence"
    assert got.certified
    assert got.structural_upgrades_checked == 2


def test_structural_upgrade_cannot_repeat_same_phase_without_numeric_shrink():
    leaf = _terminal(64, 40, PHASE_UPCC)
    root = StructuralRecurrenceAccountingNode(
        64, 40, PHASE_UPCC, "structural_upgrade", True, True, 1.0,
        (StructuralAccountingChild(leaf),), False, "invalid repeated UPCC phase",
    )
    got = validate_structural_quasipoly_recurrence_tree(root)
    assert got.status == "nonprogressing_structural_upgrade"
    assert not got.certified


def test_numeric_shrink_may_reset_structural_phase_on_smaller_instance():
    leaf = _terminal(64, 30, PHASE_CLIQUE)
    root = StructuralRecurrenceAccountingNode(
        64, 50, PHASE_JOHNSON, "aux_shrink", True, True, 1.0,
        (StructuralAccountingChild(leaf),), False, "smaller structural instance may restart",
    )
    got = validate_structural_quasipoly_recurrence_tree(root)
    assert got.certified


def test_branch_multiplicity_and_local_cost_are_still_charged_globally():
    leaf = _terminal(32, 8, PHASE_CLIQUE, cost=4.0)
    root = StructuralRecurrenceAccountingNode(
        32, 16, PHASE_UPCC, "aux_shrink", True, True, 5.0,
        (StructuralAccountingChild(leaf, multiplicity=16),), False, "sixteen exact branches",
    )
    got = validate_structural_quasipoly_recurrence_tree(root)
    assert got.certified
    assert got.log2_work_bound >= 5.0 + log2(16) + 4.0 - 1e-12


def test_small_aux_reset_still_requires_factorial_charge_and_primary_shrink():
    child = _terminal(50, 20, PHASE_CLIQUE)
    bad = StructuralRecurrenceAccountingNode(
        100, 4, PHASE_JOHNSON, "small_aux_reset", True, True, 1.0,
        (StructuralAccountingChild(child),), False, "undercharged S4",
    )
    got = validate_structural_quasipoly_recurrence_tree(bad)
    assert got.status == "undercharged_auxiliary_enumeration"
    assert not got.certified
