from __future__ import annotations

from math import log2

from coset_stabilizer_primitives import RightCoset
from orbit_action_preimage_coset_v1 import orbit_action_preimage_coset
from orbit_factored_string_coset_intersection_v1 import _image_chain
from permutation_group_schreier import compose, identity, inverse
from proof_carrying_si_v1 import ProofCarryingCoset, r1_string_isomorphism_child
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from s1_structural_classifier_v1 import classify_s1_structure


def _structural_stop(classification, *, root_n: int, children=(), reason: str | None = None):
    text = reason or classification.reason
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, classification.degree),
        operation_kind=classification.status,
        canonical=classification.canonical,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=tuple(AccountingChild(c.accounting) for c in children),
        terminal_certified=False,
        reason=text,
    )
    return ProofCarryingCoset(
        "undetermined_" + classification.status,
        None,
        classification.status,
        root_n,
        classification.degree,
        classification.canonical,
        False,
        False,
        0.0,
        False,
        tuple(children),
        accounting,
        sum(c.permutation_candidates_checked for c in children),
        text,
    )


def _orbit_partition_parent(
    *,
    root_n: int,
    degree: int,
    coset,
    exact: bool,
    children,
    status: str,
    reason: str,
):
    # Canonical orbit decomposition itself is generator-BFS/Schreier polynomial
    # work.  Charge a deliberately loose polynomial multiplicative envelope; all
    # potentially superpolynomial child work is carried by the exact child nodes.
    local_bound = 10.0 * log2(max(2, degree)) + 20.0
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, degree),
        operation_kind="orbit_partition",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=tuple(AccountingChild(c.accounting) for c in children),
        terminal_certified=False,
        reason=(
            "canonical disjoint group-orbit decomposition; child accounting is the exact set of S1 calls actually executed"
        ),
    )
    return ProofCarryingCoset(
        status,
        coset,
        "orbit_partition",
        root_n,
        degree,
        True,
        exact,
        True,
        local_bound,
        False,
        tuple(children),
        accounting,
        sum(c.permutation_candidates_checked for c in children),
        reason,
    )


def s1_string_isomorphism(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    max_depth: int = 64,
    _depth: int = 0,
) -> ProofCarryingCoset:
    """First self-recursive S1 executor.

    Resolved operators in v1:
      * T1 exact value-multiplicity / full-S_m small terminal;
      * canonical intransitive decomposition, with every orbit child recursively
        dispatched through S1 and lifted by exact paired Schreier preimages.

    Transitive imprimitive, primitive non-giant and primitive giant cases are
    structurally classified but remain explicit unresolved proof objects.  This
    is intentional: no non-polylog path falls back to the legacy node-capped SI
    search while the next structural operators are still being implemented.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    if root_n < n:
        raise ValueError("root_n must dominate current degree")
    if _depth > max_depth:
        classification = classify_s1_structure(
            group, root_n=root_n, polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
        )
        return _structural_stop(
            classification, root_n=root_n,
            reason="S1 structural recursion exceeded max_depth; fail closed",
        )

    base = r1_string_isomorphism_child(
        group, source, target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
    )
    if base.exact:
        return base

    classification = classify_s1_structure(
        group,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
    )
    if classification.status != "canonical_intransitive_partition":
        return _structural_stop(classification, root_n=root_n)

    H = group
    r = identity(n)
    children = []
    # The partition is canonical as a set.  The concrete tuple order is only an
    # execution order; exact coset composition and accounting are symmetric in
    # the disjoint children and do not use the numeric order as mathematical data.
    for O in classification.group_orbits:
        image = _image_chain(H, O)
        rinv = inverse(r)
        local_source = tuple(source[rinv[j]] for j in O)
        local_target = tuple(target[j] for j in O)
        child = s1_string_isomorphism(
            image,
            local_source,
            local_target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            max_depth=max_depth,
            _depth=_depth + 1,
        )
        children.append(child)
        if not child.exact:
            return _structural_stop(
                classification,
                root_n=root_n,
                children=tuple(children),
                reason=(
                    "canonical intransitive parent reached an unresolved structural child; exact parent result is withheld"
                ),
            )
        if child.coset is None:
            return _orbit_partition_parent(
                root_n=root_n,
                degree=n,
                coset=None,
                exact=True,
                children=tuple(children),
                status="exact_empty_orbit_partition",
                reason="one exact proof-carrying invariant-orbit child is empty, so the whole SI coset is empty",
            )

        lifted = orbit_action_preimage_coset(H, O, child.coset)
        if lifted.status != "exact_orbit_action_coset_preimage" or lifted.coset is None:
            return _structural_stop(
                classification,
                root_n=root_n,
                children=tuple(children),
                reason="an exact S1 orbit child could not be lifted by the paired-Schreier preimage operator",
            )
        H = lifted.subgroup
        r = compose(r, lifted.representative)

    result = RightCoset(H, r)
    return _orbit_partition_parent(
        root_n=root_n,
        degree=n,
        coset=result,
        exact=True,
        children=tuple(children),
        status="exact_intransitive_s1_coset",
        reason=(
            "every canonical invariant-orbit child was recursively solved by S1, exactly lifted, and composed into the final two-string isomorphism coset"
        ),
    )
