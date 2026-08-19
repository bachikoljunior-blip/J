from __future__ import annotations

from collections import Counter
from math import log2

from coset_stabilizer_primitives import RightCoset
from orbit_action_preimage_coset_v1 import orbit_action_preimage_coset
from orbit_factored_string_coset_intersection_v1 import _group_orbits, _image_chain
from permutation_group_schreier import compose, inverse
from proof_carrying_si_v1 import ProofCarryingCoset
from proof_carrying_small_order_candidate_v1 import exact_small_order_candidate_string_isomorphism
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from s1_string_isomorphism_v2 import s1_string_isomorphism_v2


def _parent(*, root_n, degree, status, coset, exact, children, cost_certified=True, reason):
    local_bound = 10.0 * log2(max(2, degree)) + 22.0 if cost_certified else 0.0
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, degree),
        operation_kind="orbit_partition" if cost_certified else "unresolved_candidate_coset",
        canonical=True,
        cost_certified=cost_certified,
        local_log2_cost_bound=local_bound,
        children=tuple(AccountingChild(c.accounting) for c in children),
        terminal_certified=False,
        reason=reason,
    )
    return ProofCarryingCoset(
        status,
        coset,
        "orbit_partition" if cost_certified else "unresolved_candidate_coset",
        root_n,
        degree,
        True,
        exact,
        cost_certified,
        local_bound,
        False,
        tuple(children),
        accounting,
        sum(c.permutation_candidates_checked for c in children),
        reason,
    )


def candidate_coset_string_isomorphism_u2(
    candidate: RightCoset,
    source_values,
    target_values,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
) -> ProofCarryingCoset:
    """Candidate-coset SI with exact small-order terminals at every orbit level.

    First enumerate H*r directly when Schreier certifies H as small.  If H is
    larger and intransitive, recurse over its canonical orbits, but use S1v2 on
    each induced image so a large-degree orbit with a small represented group is
    still solved exactly.  A genuinely large transitive H remains a typed V2
    structural leaf rather than falling back to generic node-capped search.
    """
    H0 = candidate.subgroup
    n = H0.degree
    source = tuple(source_values)
    target = tuple(target_values)
    if len(source) != n or len(target) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    try:
        if Counter(source) != Counter(target):
            local_bound = 8.0 * log2(max(2, n)) + 10.0
            accounting = RecurrenceAccountingNode(
                n=root_n,
                m=max(1, n),
                operation_kind="value_multiplicity_terminal",
                canonical=True,
                cost_certified=True,
                local_log2_cost_bound=local_bound,
                children=(),
                terminal_certified=True,
                reason="global source/target value multiplicities differ",
            )
            return ProofCarryingCoset(
                "exact_empty_value_multiplicity",
                None,
                "value_multiplicity_terminal",
                root_n,
                n,
                True,
                True,
                True,
                local_bound,
                True,
                (),
                accounting,
                0,
                "global value multiplicity mismatch proves this candidate fiber empty",
            )
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc

    small = exact_small_order_candidate_string_isomorphism(
        candidate,
        source,
        target,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
    )
    if small.exact:
        return small

    initial_orbits = _group_orbits(H0)
    if len(initial_orbits) <= 1 and n > 1:
        return _parent(
            root_n=root_n,
            degree=n,
            status="undetermined_transitive_candidate_large_order",
            coset=None,
            exact=False,
            children=(),
            cost_certified=False,
            reason="candidate subgroup is transitive and above the exact-order cap; canonical structural quotient/local-certificate recursion is still required",
        )

    H = H0
    r = candidate.representative
    children = []
    for orbit in initial_orbits:
        image = _image_chain(H, orbit)
        rinv = inverse(r)
        local_source = tuple(source[rinv[j]] for j in orbit)
        local_target = tuple(target[j] for j in orbit)
        child = s1_string_isomorphism_v2(
            image,
            local_source,
            local_target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=group_order_poly_power,
            max_group_order=max_group_order,
            max_depth=max_depth,
        )
        children.append(child)
        if not child.exact:
            return _parent(
                root_n=root_n,
                degree=n,
                status=child.status,
                coset=None,
                exact=False,
                children=tuple(children),
                cost_certified=False,
                reason="candidate fiber reached an unresolved large-order structural orbit child; exact parent result withheld",
            )
        if child.coset is None:
            return _parent(
                root_n=root_n,
                degree=n,
                status="exact_empty_candidate_orbit_partition_v2",
                coset=None,
                exact=True,
                children=tuple(children),
                reason="one exact S1v2 subgroup-orbit child is empty, proving this candidate fiber empty",
            )

        lifted = orbit_action_preimage_coset(H, orbit, child.coset)
        if lifted.status != "exact_orbit_action_coset_preimage" or lifted.coset is None:
            return _parent(
                root_n=root_n,
                degree=n,
                status="undetermined_candidate_child_preimage_v2",
                coset=None,
                exact=False,
                children=tuple(children),
                cost_certified=False,
                reason="an exact S1v2 child could not be lifted through the subgroup orbit action",
            )
        H = lifted.subgroup
        r = compose(r, lifted.representative)

    return _parent(
        root_n=root_n,
        degree=n,
        status="exact_candidate_coset_string_isomorphism_v2",
        coset=RightCoset(H, r),
        exact=True,
        children=tuple(children),
        reason="all candidate-subgroup invariant orbit children were solved with S1v2 and exactly lifted; the returned coset is precisely the fiber string intersection",
    )
