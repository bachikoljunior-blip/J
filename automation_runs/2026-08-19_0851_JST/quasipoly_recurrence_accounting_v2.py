from __future__ import annotations

from math import lgamma, log, log2

from quasipoly_recurrence_accounting_v1 import (
    QuasipolyAccountingValidation,
    RecurrenceAccountingNode,
)


def _log2_sum_exp(values):
    values = tuple(values)
    if not values:
        return 0.0
    top = max(values)
    return top + log2(sum(2.0 ** (v - top) for v in values))


def _log2_factorial(k: int) -> float:
    if k < 0:
        raise ValueError("factorial input must be nonnegative")
    return lgamma(k + 1) / log(2.0)


def validate_quasipoly_recurrence_tree_v2(
    root: RecurrenceAccountingNode,
    *,
    shrink_fraction: float = 0.9,
    polylog_power: int = 2,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> QuasipolyAccountingValidation:
    """rev150 verifier plus exact canonical disjoint-orbit composition.

    `orbit_partition` is an additive structural decomposition, not a branching
    enumeration.  It is accepted only if all child auxiliary domains are strictly
    smaller, all children keep the same primary n, and the multiplicity-weighted
    child domains fit inside the parent auxiliary domain.  This mechanically
    prevents an orbit partition from being used to hide duplicated or overlapping
    recursive work.  Existing aux_shrink and small_aux_reset rules are unchanged.
    """
    if not (0.0 < shrink_fraction < 1.0):
        raise ValueError("shrink_fraction must be in (0,1)")
    if polylog_power < 1 or quasipoly_power < 1 or quasipoly_constant <= 0:
        raise ValueError("invalid quasipolynomial parameters")
    if root.n <= 0 or root.m <= 0 or root.m > root.n:
        return QuasipolyAccountingValidation(
            "invalid_root_measure", False, 0.0, 0.0, 0, 0,
            "root requires 1 <= m <= n",
        )

    root_n = root.n
    allowed = quasipoly_constant * (log2(max(2, root_n)) ** quasipoly_power)
    seen_ids = set()
    nodes_checked = 0
    max_depth = 0

    class Invalid(Exception):
        def __init__(self, status, reason):
            self.status = status
            self.reason = reason

    def rec(node, depth):
        nonlocal nodes_checked, max_depth
        oid = id(node)
        if oid in seen_ids:
            raise Invalid("cyclic_accounting_trace", "recurrence accounting graph must be acyclic")
        seen_ids.add(oid)
        nodes_checked += 1
        max_depth = max(max_depth, depth)

        if node.n <= 0 or node.m <= 0 or node.m > node.n:
            raise Invalid("invalid_measure", "every node requires 1 <= m <= n")
        if not node.canonical:
            raise Invalid("noncanonical_accounting_step", "every accounted step must be label-invariant")
        if not node.cost_certified:
            raise Invalid("uncertified_local_cost", "local multiplicative cost lacks an external/mechanical upper-bound certificate")
        if node.local_log2_cost_bound < 0:
            raise Invalid("invalid_local_cost", "local log2 cost bound must be nonnegative")

        if not node.children:
            if not node.terminal_certified:
                raise Invalid("uncertified_terminal", "leaf lacks an exact/certified terminal condition")
            seen_ids.remove(oid)
            return float(node.local_log2_cost_bound)
        if node.terminal_certified:
            raise Invalid("terminal_with_children", "a certified terminal may not also recurse")

        threshold = max(1.0, log2(max(2, node.n)) ** polylog_power)
        if node.operation_kind == "orbit_partition":
            weighted = sum(edge.multiplicity * edge.node.m for edge in node.children)
            if weighted > node.m:
                raise Invalid(
                    "overlapping_or_duplicated_orbit_children",
                    "orbit_partition child domains, with multiplicity, exceed the parent auxiliary domain",
                )

        child_terms = []
        for edge in node.children:
            if edge.multiplicity <= 0:
                raise Invalid("invalid_branch_multiplicity", "child multiplicities must be positive")
            child = edge.node
            if child.n > node.n or child.m > child.n:
                raise Invalid("measure_increase", "recurrence may not increase n and always requires m<=n")

            if node.operation_kind == "aux_shrink":
                if child.m > shrink_fraction * node.m + 1e-12:
                    raise Invalid("insufficient_auxiliary_shrink", "aux_shrink must reduce m by the configured constant fraction")
            elif node.operation_kind == "small_aux_reset":
                if node.m > threshold + 1e-12:
                    raise Invalid("premature_auxiliary_enumeration", "brute-force/reset is permitted only once m is polylogarithmic in n")
                if child.n > shrink_fraction * node.n + 1e-12:
                    raise Invalid("insufficient_primary_shrink", "small_aux_reset must significantly reduce n")
                required = _log2_factorial(node.m)
                if node.local_log2_cost_bound + 1e-12 < required:
                    raise Invalid("undercharged_auxiliary_enumeration", "declared cost does not cover enumeration of S_m")
            elif node.operation_kind == "orbit_partition":
                if child.n != node.n:
                    raise Invalid("orbit_partition_primary_measure_changed", "orbit_partition is additive at fixed primary n")
                if child.m >= node.m:
                    raise Invalid("nonshrinking_orbit_child", "every orbit_partition child must have strictly smaller auxiliary domain")
            else:
                raise Invalid("unknown_progress_kind", "nonterminal operation must be aux_shrink, small_aux_reset, or orbit_partition")

            sub = rec(child, depth + 1)
            child_terms.append(log2(edge.multiplicity) + sub)

        total = float(node.local_log2_cost_bound) + _log2_sum_exp(child_terms)
        seen_ids.remove(oid)
        return total

    try:
        work = rec(root, 0)
    except Invalid as exc:
        return QuasipolyAccountingValidation(
            exc.status, False, 0.0, allowed, nodes_checked, max_depth, exc.reason
        )

    if work > allowed + 1e-9:
        return QuasipolyAccountingValidation(
            "quasipolynomial_bound_exceeded", False, work, allowed,
            nodes_checked, max_depth,
            "certified local bounds compose to more than the configured quasipolynomial envelope",
        )
    return QuasipolyAccountingValidation(
        "certified_quasipolynomial_recurrence", True, work, allowed,
        nodes_checked, max_depth,
        "all branches are canonical, locally cost-certified, use an approved structural progress rule, and compose within the configured quasipolynomial envelope",
    )
