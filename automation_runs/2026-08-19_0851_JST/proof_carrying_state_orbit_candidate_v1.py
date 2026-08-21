from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import factorial, log2

from coset_stabilizer_primitives import RightCoset
from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add, _sat_mul
from permutation_group_schreier import compose, identity, inverse
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from state_orbit_schreier import string_orbit_stabilizer_transporter


@dataclass(frozen=True)
class StateOrbitCandidateEnvelope:
    degree: int
    group_order: int
    generator_count: int
    multiset_image_upper_bound: int
    state_image_upper_bound: int
    work_upper_bound: int
    max_work: int
    admitted: bool


def _multiset_permutation_count(values) -> int:
    values = tuple(values)
    try:
        counts = Counter(values)
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc
    out = factorial(len(values))
    for count in counts.values():
        out //= factorial(count)
    return out


def state_orbit_candidate_envelope(candidate, target_values, *, max_work: int):
    """Reserve the complete string-image orbit and its Schreier stabilizer.

    The induced orbit contains at most both ``|G|`` states and the number of
    distinct permutations of the target multiset.  The bound is input-derived,
    arbitrary precision and checked before the state-orbit search starts.
    """
    group = candidate.subgroup
    target = tuple(target_values)
    if len(target) != group.degree:
        raise ValueError("string/candidate degree mismatch")
    cap = int(max_work)
    if cap <= 0:
        raise ValueError("max_work must be positive")
    n = group.degree
    g = max(1, len(group.original_generators))
    multiset = _multiset_permutation_count(target)
    states = min(int(group.order), multiset)
    stop = cap + 1
    action = _sat_mul(states, _sat_mul(g, max(1, n), stop), stop)
    # At most one Schreier generator is emitted per state-generator edge.
    chain = _chain_bound(n, states * g, int(group.order), n, stop)
    work = _sat_add(action, chain, stop)
    return StateOrbitCandidateEnvelope(
        n, int(group.order), g, multiset, states, work, cap, work <= cap
    )


def exact_state_orbit_candidate_string_isomorphism(
    candidate,
    source_values,
    target_values,
    *,
    root_n: int,
    max_work: int,
) -> ProofCarryingCoset:
    """Solve one candidate fiber by a completely reserved string-state orbit.

    This is an exact terminal, not a structural-path prediction.  It is invoked
    only when the complete state orbit and stabilizer-chain work were admitted
    up front.  The subgroup returned by the state-orbit algorithm is the exact
    target-string stabilizer, so no later intransitive/imprimitive/primitive
    recursion is required for this candidate fiber.
    """
    group = candidate.subgroup
    n = group.degree
    source = tuple(source_values)
    target = tuple(target_values)
    if len(source) != n or len(target) != n or root_n < n:
        raise ValueError("invalid state-orbit candidate dimensions")
    envelope = state_orbit_candidate_envelope(candidate, target, max_work=max_work)
    if not envelope.admitted:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, n), operation_kind="unresolved_state_orbit_terminal",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="complete string-state orbit exceeds the finite pre-execution budget",
        )
        return ProofCarryingCoset(
            "undetermined_state_orbit_work_cap", None,
            "unresolved_state_orbit_terminal", root_n, n, True, False, False,
            0.0, False, (), accounting, 0,
            "complete string-state orbit exceeds the finite pre-execution budget",
        )

    rinv = inverse(candidate.representative)
    subgroup_source = tuple(source[rinv[j]] for j in range(n))
    generators = group.original_generators or (identity(n),)
    exact = string_orbit_stabilizer_transporter(
        generators, subgroup_source, target,
        max_images=envelope.state_image_upper_bound,
    )
    if exact.status == "undetermined_image_orbit_limit":
        raise AssertionError("admitted state-image upper bound was exceeded")
    local_bound = log2(max(1, envelope.work_upper_bound)) + 8.0 * log2(max(2, n)) + 16.0
    empty = exact.status == "empty_transporter"
    if exact.status not in {"empty_transporter", "exact_transporter_coset"}:
        raise AssertionError("unexpected exact state-orbit status")
    result = None
    if not empty:
        inner = exact.transporter
        if inner is None:
            raise AssertionError("exact state transporter omitted its right coset")
        result = RightCoset(
            inner.subgroup,
            compose(candidate.representative, inner.representative),
        )
    reason = (
        "complete reserved string-state orbit proved the candidate fiber empty"
        if empty else
        "complete reserved string-state orbit returned the exact target-stabilizer right coset"
    )
    accounting = RecurrenceAccountingNode(
        n=root_n, m=max(1, n), operation_kind="state_orbit_si_terminal",
        canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
        children=(), terminal_certified=True, reason=reason,
    )
    return ProofCarryingCoset(
        "exact_empty_state_orbit_candidate" if empty else "exact_state_orbit_candidate_coset",
        result, "state_orbit_si_terminal", root_n, n, True, True, True,
        local_bound, True, (), accounting, exact.orbit_size, reason,
    )


__all__ = [
    "StateOrbitCandidateEnvelope",
    "state_orbit_candidate_envelope",
    "exact_state_orbit_candidate_string_isomorphism",
]
