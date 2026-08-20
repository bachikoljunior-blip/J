from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from math import factorial, lgamma, log, log2
from typing import Optional, Tuple

from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class ProofCarryingCoset:
    status: str
    coset: Optional[RightCoset]
    operation_kind: str
    root_n: int
    domain_size: int
    canonical: bool
    exact: bool
    local_cost_certified: bool
    local_log2_cost_bound: float
    terminal_certified: bool
    children: Tuple["ProofCarryingCoset", ...]
    accounting: RecurrenceAccountingNode
    permutation_candidates_checked: int
    reason: str
    proof_identity: object | None = None


def _log2_factorial(k: int) -> float:
    if k < 0:
        raise ValueError("factorial input must be nonnegative")
    return lgamma(k + 1) / log(2.0)


def _uncertified_leaf(status: str, *, root_n: int, m: int, reason: str) -> ProofCarryingCoset:
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, m),
        operation_kind="unresolved_r1_dispatch",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=(),
        terminal_certified=False,
        reason=reason,
    )
    return ProofCarryingCoset(
        status, None, "unresolved_r1_dispatch", root_n, m,
        True, False, False, 0.0, False, (), accounting, 0, reason,
    )


def explicit_small_coset_intersection_proof(
    a: RightCoset,
    b: RightCoset,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
) -> ProofCarryingCoset:
    """Exact small-domain coset intersection with execution/accounting identity.

    This terminal enumerates the full symmetric group on the child domain.  It is
    allowed only when the child degree is within the configured polylogarithmic
    auxiliary window and within the explicit implementation cap.  The exact same
    enumeration that computes the intersection supplies the terminal cost witness;
    no node-cap search is reinterpreted as a complexity certificate.

    The local multiplicative charge is deliberately conservative: two complete
    S_m scans plus an m^8 polynomial envelope for membership/reconstruction work.
    This is an execution-derived bound, not an empirical timing claim.
    """
    if a.subgroup.degree != b.subgroup.degree:
        raise ValueError("degree mismatch")
    m = a.subgroup.degree
    if root_n < m or root_n <= 0:
        raise ValueError("root_n must be positive and at least the child degree")
    if polylog_power < 1 or max_explicit_degree < 1:
        raise ValueError("invalid terminal parameters")

    threshold = max(1.0, log2(max(2, root_n)) ** polylog_power)
    if m > threshold + 1e-12:
        return _uncertified_leaf(
            "undetermined_nonpolylog_child_requires_r1",
            root_n=root_n,
            m=m,
            reason=(
                "child domain exceeds the configured polylogarithmic terminal window; "
                "an opaque exact/node-capped terminal is forbidden and structural R1 recursion is required"
            ),
        )
    if m > max_explicit_degree:
        return _uncertified_leaf(
            "undetermined_explicit_terminal_cap",
            root_n=root_n,
            m=m,
            reason=(
                "child is inside the mathematical polylog terminal window but exceeds the current explicit "
                "full-S_m implementation cap; fail closed rather than substituting a node cap"
            ),
        )

    universe = tuple(permutations(range(m)))
    intersection = tuple(p for p in universe if a.contains(p) and b.contains(p))
    checked = len(universe)

    if not intersection:
        # Empty is an exact terminal too; the second full scan below is unnecessary
        # because there is no reconstructed coset to audit.
        local_bound = log2(max(1, checked)) + 8.0 * log2(max(2, m)) + 16.0
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, m),
            operation_kind="explicit_small_si_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="full S_m enumeration proved the two right cosets disjoint",
        )
        return ProofCarryingCoset(
            "exact_empty_small_terminal", None, "explicit_small_si_terminal",
            root_n, m, True, True, True, local_bound, True, (), accounting,
            checked,
            "full symmetric-domain enumeration proved the child intersection empty",
        )

    witness = min(intersection)
    translated = tuple(compose(inverse(witness), p) for p in intersection)
    subgroup = schreier_stabilizer_chain(translated or (identity(m),))
    result = RightCoset(subgroup, witness)
    if subgroup.order != len(intersection):
        raise AssertionError("translated exact intersection did not reconstruct the expected subgroup order")
    if any(not result.contains(p) for p in intersection):
        raise AssertionError("reconstructed exact child coset lost an enumerated intersection element")

    # A second complete scan proves the reconstructed coset has no extra elements.
    reconstructed = tuple(p for p in universe if result.contains(p))
    checked += len(universe)
    if reconstructed != intersection:
        raise AssertionError("reconstructed child coset differs from the enumerated exact intersection")

    # 2*m! candidate scans plus a deliberately loose polynomial envelope for
    # Schreier membership and reconstruction.  The factorial term is the relevant
    # Babai small-auxiliary multiplicative charge.
    local_bound = _log2_factorial(m) + 8.0 * log2(max(2, m)) + 18.0
    if local_bound + 1e-12 < log2(max(1, checked)):
        raise AssertionError("mechanical local charge does not dominate executed candidate scans")
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, m),
        operation_kind="explicit_small_si_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=True,
        reason="exact full-S_m child intersection; execution and terminal accounting are the same object",
    )
    return ProofCarryingCoset(
        "exact_small_intersection_coset", result, "explicit_small_si_terminal",
        root_n, m, True, True, True, local_bound, True, (), accounting,
        checked,
        "full symmetric-domain enumeration returned the exact child coset and its mechanically charged terminal proof",
    )


def r1_string_isomorphism_child(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
) -> ProofCarryingCoset:
    """First R1 child dispatcher: exact small terminal, otherwise fail closed.

    This deliberately replaces the former non-polylog node-capped exact search.
    Large children are not declared solved: they return a typed unresolved R1
    proof object that must be consumed by the next structural recursive handler.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    if len(source) != group.degree or len(target) != group.degree:
        raise ValueError("string/group degree mismatch")
    value_coset = _all_value_preserving_maps(source, target)
    if value_coset is None:
        m = group.degree
        local_bound = 8.0 * log2(max(2, m)) + 8.0
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, m),
            operation_kind="value_multiplicity_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="value multiplicity mismatch is a canonical exact emptiness certificate",
        )
        return ProofCarryingCoset(
            "exact_empty_value_multiplicity", None, "value_multiplicity_terminal",
            root_n, m, True, True, True, local_bound, True, (), accounting, 0,
            "source and target value multiplicities differ",
        )
    return explicit_small_coset_intersection_proof(
        RightCoset(group, identity(group.degree)),
        value_coset,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
    )
