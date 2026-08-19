from __future__ import annotations

from collections import Counter
from math import log2

from coset_stabilizer_primitives import RightCoset
from orbit_action_preimage_coset_v1 import orbit_action_preimage_coset
from orbit_factored_string_coset_intersection_v1 import _group_orbits, _image_chain
from permutation_group_schreier import compose, inverse
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from s1_string_isomorphism_v1 import s1_string_isomorphism


def _parent(
    *,
    root_n,
    degree,
    status,
    coset,
    exact,
    children,
    cost_certified=True,
    reason,
):
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
        status, coset,
        "orbit_partition" if cost_certified else "unresolved_candidate_coset",
        root_n, degree, True, exact, cost_certified, local_bound,
        False, tuple(children), accounting,
        sum(c.permutation_candidates_checked for c in children), reason,
    )


def candidate_coset_string_isomorphism_u1(
    candidate: RightCoset,
    source_values,
    target_values,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    max_depth: int = 64,
) -> ProofCarryingCoset:
    """Intersect one exact right-coset fiber with two strings using U1 children.

    This is the coset-valued analogue of rev165's intransitive group recursion.
    It is intended for quotient/kernel fibers whose subgroup is already known to
    be intransitive.  Every subgroup orbit is an exact target-side invariant
    domain.  The source segment is pulled through the current representative,
    recursively solved in the induced orbit action, then exactly lifted through
    paired Schreier preimages.

    A transitive candidate subgroup is deliberately rejected rather than routed
    to a generic point-image/node-capped exact intersection.  U2 must first expose
    structural quotient/kernel progress.
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
            # Any permutation is a bijection, so this proves emptiness independent
            # of the candidate fiber.  Keep it as a certified exact leaf.
            local_bound = 8.0 * log2(max(2, n)) + 10.0
            accounting = RecurrenceAccountingNode(
                n=root_n, m=max(1, n), operation_kind="value_multiplicity_terminal",
                canonical=True, cost_certified=True,
                local_log2_cost_bound=local_bound, children=(),
                terminal_certified=True,
                reason="global source/target value multiplicities differ",
            )
            return ProofCarryingCoset(
                "exact_empty_value_multiplicity", None, "value_multiplicity_terminal",
                root_n, n, True, True, True, local_bound, True, (), accounting, 0,
                "global value multiplicity mismatch proves this candidate fiber empty",
            )
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc

    initial_orbits = _group_orbits(H0)
    if len(initial_orbits) <= 1 and n > 1:
        return _parent(
            root_n=root_n, degree=n,
            status="undetermined_transitive_candidate_requires_u2",
            coset=None, exact=False, children=(), cost_certified=False,
            reason="candidate subgroup is transitive; structural U2 recursion is required before string intersection",
        )

    H = H0
    r = candidate.representative
    children = []
    for O in initial_orbits:
        image = _image_chain(H, O)
        rinv = inverse(r)
        local_source = tuple(source[rinv[j]] for j in O)
        local_target = tuple(target[j] for j in O)
        child = s1_string_isomorphism(
            image, local_source, local_target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            max_depth=max_depth,
        )
        children.append(child)
        if not child.exact:
            return _parent(
                root_n=root_n, degree=n,
                status=child.status, coset=None, exact=False,
                children=tuple(children), cost_certified=False,
                reason="candidate fiber reached an unresolved U1/U2 orbit child; exact parent result withheld",
            )
        if child.coset is None:
            return _parent(
                root_n=root_n, degree=n,
                status="exact_empty_candidate_orbit_partition",
                coset=None, exact=True, children=tuple(children),
                reason="one exact proof-carrying subgroup-orbit child is empty, proving this quotient fiber empty",
            )

        lifted = orbit_action_preimage_coset(H, O, child.coset)
        if lifted.status != "exact_orbit_action_coset_preimage" or lifted.coset is None:
            return _parent(
                root_n=root_n, degree=n,
                status="undetermined_candidate_child_preimage",
                coset=None, exact=False, children=tuple(children), cost_certified=False,
                reason="an exact U1 child could not be lifted through the subgroup orbit action",
            )
        H = lifted.subgroup
        r = compose(r, lifted.representative)

    return _parent(
        root_n=root_n, degree=n,
        status="exact_candidate_coset_string_isomorphism",
        coset=RightCoset(H, r), exact=True, children=tuple(children),
        reason="all candidate-subgroup invariant orbit children were recursively solved and exactly lifted; the returned coset is precisely the fiber string intersection",
    )
