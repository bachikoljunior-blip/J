from __future__ import annotations

from dataclasses import dataclass
from math import log2

from certified_group_enumeration_v1 import enumerate_schreier_group_exact
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class SmallOrderCandidateProof(ProofCarryingCoset):
    subgroup_elements_checked: int = 0
    certified_subgroup_order: int = 0


def exact_small_order_candidate_string_isomorphism(
    candidate: RightCoset,
    source_values,
    target_values,
    *,
    root_n: int,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
) -> SmallOrderCandidateProof:
    """Exactly intersect H*r with two strings when the certified |H| is small.

    RightCoset.contains uses r^{-1}p in H under this repository's composition
    convention, hence the candidate elements are compose(r, h) for h in H.
    We enumerate H only after its Schreier-certified order passes the configured
    polynomial and implementation caps, test every candidate element, then audit
    the nonempty result by reconstructing its translated subgroup and rescanning
    the complete candidate coset.
    """
    H = candidate.subgroup
    r = candidate.representative
    source = tuple(source_values)
    target = tuple(target_values)
    n = H.degree
    if len(source) != n or len(target) != n or len(r) != n:
        raise ValueError("string/candidate degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")
    if group_order_poly_power < 1 or max_group_order < 1:
        raise ValueError("invalid candidate enumeration parameters")

    allowed = min(max_group_order, root_n ** group_order_poly_power)
    if H.order > allowed:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, n),
            operation_kind="small_order_candidate_cap",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason="candidate subgroup order exceeds the polynomial/implementation enumeration cap",
        )
        return SmallOrderCandidateProof(
            "undetermined_candidate_group_order_cap",
            None,
            "small_order_candidate_cap",
            root_n,
            n,
            True,
            False,
            False,
            0.0,
            False,
            (),
            accounting,
            0,
            "candidate subgroup is too large for exact coset enumeration; structural recursion remains required",
            subgroup_elements_checked=0,
            certified_subgroup_order=H.order,
        )

    elements = enumerate_schreier_group_exact(H, max_elements=allowed)
    if elements is None or len(elements) != H.order:
        raise AssertionError("candidate order gate admitted H but exact enumeration did not match its Schreier order")

    candidates = tuple(compose(r, h) for h in elements)
    if any(not candidate.contains(p) for p in candidates):
        raise AssertionError("enumerated H element produced a permutation outside H*r")
    matches = tuple(
        p for p in candidates
        if all(source[i] == target[p[i]] for i in range(n))
    )
    checked = len(candidates)
    local_bound = log2(max(1, H.order)) + 12.0 * log2(max(2, n)) + 24.0
    if local_bound + 1e-12 < log2(max(1, checked)):
        raise AssertionError("candidate terminal charge does not dominate exact coset scan")

    if not matches:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, n),
            operation_kind="small_order_candidate_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="complete enumeration of the certified candidate subgroup found no string isomorphism in H*r",
        )
        return SmallOrderCandidateProof(
            "exact_empty_small_order_candidate",
            None,
            "small_order_candidate_terminal",
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
            "every element of the exact candidate coset was tested and none maps source to target",
            subgroup_elements_checked=len(elements),
            certified_subgroup_order=H.order,
        )

    witness = min(matches)
    translated = tuple(compose(inverse(witness), p) for p in matches)
    subgroup = schreier_stabilizer_chain(translated)
    result = RightCoset(subgroup, witness)
    if subgroup.order != len(matches):
        raise AssertionError("translated candidate matches did not reconstruct the expected subgroup order")
    if any(not result.contains(p) for p in matches):
        raise AssertionError("reconstructed candidate SI coset lost an enumerated match")

    reconstructed = tuple(p for p in candidates if result.contains(p))
    checked += len(candidates)
    if reconstructed != matches:
        raise AssertionError("reconstructed candidate SI coset differs from exact enumerated matches")
    if local_bound + 1e-12 < log2(max(1, checked)):
        raise AssertionError("candidate terminal charge does not dominate reconstruction audit")

    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="small_order_candidate_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=True,
        reason="complete candidate-coset enumeration plus second-pass exact coset reconstruction audit",
    )
    return SmallOrderCandidateProof(
        "exact_small_order_candidate_coset",
        result,
        "small_order_candidate_terminal",
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
        "the exact string-isomorphism subset of H*r was enumerated and reconstructed as one right coset",
        subgroup_elements_checked=len(elements),
        certified_subgroup_order=H.order,
    )
