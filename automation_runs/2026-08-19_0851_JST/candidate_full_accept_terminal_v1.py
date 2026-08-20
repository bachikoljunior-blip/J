from __future__ import annotations

from math import log2

from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


def _maps_string(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def _stabilizes_string(values, p):
    return all(values[i] == values[p[i]] for i in range(len(values)))


def exact_if_entire_candidate_maps_string(candidate, source_values, target_values, *, root_n: int):
    """Accept an entire right-coset candidate when it is already inside SI.

    For a right coset H*r, if r transports source to target and every generator
    of H stabilizes target, then every h*r is a string transporter.  Since the
    caller is intersecting this exact candidate with String Isomorphism, the
    complete intersection is the candidate itself.  Failure of either check is
    deliberately only undetermined: another element of H*r may still work.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    H = candidate.subgroup
    n = H.degree
    if len(source) != n or len(target) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    rep_maps = _maps_string(source, target, candidate.representative)
    generators_stabilize = all(
        _stabilizes_string(target, g) for g in H.original_generators
    )
    checked = 1 + len(H.original_generators)

    if rep_maps and generators_stabilize:
        local_bound = log2(max(1, checked * max(1, n))) + 12.0 * log2(max(2, root_n)) + 20.0
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, n),
            operation_kind="candidate_full_accept_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="candidate representative transports the string and every subgroup generator stabilizes the target string",
        )
        return ProofCarryingCoset(
            "exact_entire_candidate_string_isomorphism",
            candidate,
            "candidate_full_accept_terminal",
            root_n,
            n,
            True,
            True,
            True,
            local_bound,
            True,
            (),
            accounting,
            checked,
            "all elements of the exact right-coset candidate H*r transport source to target, so candidate intersection with SI equals H*r",
        )

    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="candidate_full_accept_probe",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=log2(max(1, checked * max(1, n))) + 8.0 * log2(max(2, root_n)) + 12.0,
        children=(),
        terminal_certified=False,
        reason="full-candidate acceptance criterion did not fire; no emptiness or completeness conclusion is claimed",
    )
    return ProofCarryingCoset(
        "undetermined_candidate_not_fully_accepted",
        None,
        "candidate_full_accept_probe",
        root_n,
        n,
        True,
        False,
        True,
        accounting.local_log2_cost_bound,
        False,
        (),
        accounting,
        checked,
        "candidate may still have a nonempty SI intersection; only the sufficient all-elements acceptance test failed",
    )


__all__ = ["exact_if_entire_candidate_maps_string"]
