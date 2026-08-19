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
        progress_certified=True,
        local_log2_cost_bound=cost,
        children=(),
        terminal_certified=True,
        reason="exact test terminal",
    )


def _node(n, m, phase, kind, cost, child, *, progress=True, multiplicity=1, reason="test step"):
    return StructuralRecurrenceAccountingNode(
        n=n,
        m=m,
        structural_phase=phase,
        operation_kind=kind,
        canonical=True,
        cost_certified=True,
        progress_certified=progress,
        local_log2_cost_bound=cost,
        children=(StructuralAccountingChild(child, multiplicity=multiplicity),),
        terminal_certified=False,
        reason=reason,
    )


def test_certified_finite_structural_rank_then_numeric_shrink_is_valid_progress():
    leaf = _terminal(128, 50, PHASE_CLIQUE)
    johnson = _node(
        128, 100, PHASE_JOHNSON, "aux_shrink", 3.0, leaf,
        reason="independently certified Johnson-ground auxiliary shrink",
    )
    upcc = _node(
        128, 100, PHASE_UPCC, "structural_upgrade", 3.0, johnson,
        reason="independently certified UPCC-to-Johnson algorithm step",
    )
    clique = _node(
        128, 100, PHASE_CLIQUE, "structural_upgrade", 3.0, upcc,
        reason="independently certified clique-to-UPCC algorithm step",
    )
    got = validate_structural_quasipoly_recurrence_tree(clique)
    assert got.status == "certified_structural_quasipolynomial_recurrence"
    assert got.certified
    assert got.structural_upgrades_checked == 2


def test_structural_upgrade_requires_independent_progress_certificate():
    leaf = _terminal(64, 40, PHASE_UPCC)
    root = _node(
        64, 40, PHASE_CLIQUE, "structural_upgrade", 1.0, leaf,
        progress=False,
        reason="phase names alone are not theorem evidence",
    )
    got = validate_structural_quasipoly_recurrence_tree(root)
    assert got.status == "uncertified_progress_step"
    assert not got.certified


def test_structural_upgrade_cannot_repeat_same_phase_without_numeric_shrink():
    leaf = _terminal(64, 40, PHASE_UPCC)
    root = _node(
        64, 40, PHASE_UPCC, "structural_upgrade", 1.0, leaf,
        reason="invalid repeated UPCC phase",
    )
    got = validate_structural_quasipoly_recurrence_tree(root)
    assert got.status == "nonprogressing_structural_upgrade"
    assert not got.certified


def test_numeric_shrink_may_reset_structural_phase_on_smaller_instance():
    leaf = _terminal(64, 30, PHASE_CLIQUE)
    root = _node(
        64, 50, PHASE_JOHNSON, "aux_shrink", 1.0, leaf,
        reason="smaller structural instance may restart",
    )
    got = validate_structural_quasipoly_recurrence_tree(root)
    assert got.certified


def test_branch_multiplicity_and_local_cost_are_still_charged_globally():
    leaf = _terminal(32, 8, PHASE_CLIQUE, cost=4.0)
    root = _node(
        32, 16, PHASE_UPCC, "aux_shrink", 5.0, leaf,
        multiplicity=16,
        reason="sixteen exact branches",
    )
    got = validate_structural_quasipoly_recurrence_tree(root)
    assert got.certified
    assert got.log2_work_bound >= 5.0 + log2(16) + 4.0 - 1e-12


def test_small_aux_reset_still_requires_factorial_charge_and_primary_shrink():
    child = _terminal(50, 20, PHASE_CLIQUE)
    bad = _node(
        100, 4, PHASE_JOHNSON, "small_aux_reset", 1.0, child,
        reason="undercharged S4",
    )
    got = validate_structural_quasipoly_recurrence_tree(bad)
    assert got.status == "undercharged_auxiliary_enumeration"
    assert not got.certified
