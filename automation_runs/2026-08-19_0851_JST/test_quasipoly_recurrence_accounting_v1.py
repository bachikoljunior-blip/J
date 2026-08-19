from math import lgamma, log

from quasipoly_recurrence_accounting_v1 import (
    AccountingChild,
    RecurrenceAccountingNode,
    validate_quasipoly_recurrence_tree,
)


def log2_factorial(k):
    return lgamma(k + 1) / log(2.0)


def terminal(n, m=1, cost=1.0):
    return RecurrenceAccountingNode(
        n=n,
        m=m,
        operation_kind="terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=cost,
        terminal_certified=True,
    )


def test_certified_double_recurrence_composes_inside_quasipoly_envelope():
    leaf = terminal(900)
    reset = RecurrenceAccountingNode(
        n=1024,
        m=80,
        operation_kind="small_aux_reset",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=log2_factorial(80) + 2,
        children=(AccountingChild(leaf, multiplicity=2),),
    )
    root = RecurrenceAccountingNode(
        n=1024,
        m=100,
        operation_kind="aux_shrink",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=12,
        children=(AccountingChild(reset, multiplicity=4),),
    )
    r = validate_quasipoly_recurrence_tree(root)
    assert r.status == "certified_quasipolynomial_recurrence"
    assert r.certified
    assert r.nodes_checked == 3
    assert r.log2_work_bound <= r.allowed_log2_work


def test_auxiliary_nonshrink_fails_closed():
    child = terminal(1000, 95)
    root = RecurrenceAccountingNode(
        1024, 100, "aux_shrink", True, True, 1.0,
        (AccountingChild(child),), False,
    )
    assert validate_quasipoly_recurrence_tree(root).status == "insufficient_auxiliary_shrink"


def test_uncertified_local_cost_fails_closed():
    root = RecurrenceAccountingNode(
        100, 10, "terminal", True, False, 1.0, (), True
    )
    assert validate_quasipoly_recurrence_tree(root).status == "uncertified_local_cost"


def test_reset_before_polylog_threshold_fails_closed():
    child = terminal(800)
    root = RecurrenceAccountingNode(
        1024, 200, "small_aux_reset", True, True,
        log2_factorial(200), (AccountingChild(child),), False,
    )
    assert validate_quasipoly_recurrence_tree(root).status == "premature_auxiliary_enumeration"


def test_undercharged_small_aux_enumeration_fails_closed():
    child = terminal(900)
    root = RecurrenceAccountingNode(
        1024, 80, "small_aux_reset", True, True,
        1.0, (AccountingChild(child),), False,
    )
    assert validate_quasipoly_recurrence_tree(root).status == "undercharged_auxiliary_enumeration"


def test_global_cost_overflow_fails_closed_even_for_terminal():
    root = terminal(1024, cost=10_000_000.0)
    r = validate_quasipoly_recurrence_tree(root)
    assert r.status == "quasipolynomial_bound_exceeded"
    assert not r.certified
