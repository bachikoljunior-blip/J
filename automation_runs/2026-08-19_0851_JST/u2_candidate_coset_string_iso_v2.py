from __future__ import annotations

from collections import Counter
from dataclasses import replace
from math import log2

from coset_stabilizer_primitives import RightCoset
from orbit_action_preimage_coset_v1 import orbit_action_preimage_coset
from orbit_factored_string_coset_intersection_v1 import _group_orbits, _image_chain
from permutation_group_schreier import compose, inverse
from primitive_johnson_ground_terminal_v1 import primitive_johnson_ground_string_isomorphism_terminal
from proof_carrying_si_v1 import ProofCarryingCoset
from proof_carrying_small_order_candidate_v1 import exact_small_order_candidate_string_isomorphism
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from s1_string_isomorphism_v2 import s1_string_isomorphism_v2
from s1_structural_classifier_v1 import classify_s1_structure
from signed_johnson_ground_profile_partition_si_v1 import signed_johnson_ground_profile_partition_si


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


def _translate_subgroup_si_back_to_candidate(inner, representative, *, degree):
    if not inner.exact:
        raise ValueError("translation requires an exact subgroup SI result")
    extra_bound = 4.0 * log2(max(2, degree)) + 12.0
    accounting = replace(
        inner.accounting,
        local_log2_cost_bound=inner.accounting.local_log2_cost_bound + extra_bound,
        reason=inner.accounting.reason + "; exact fixed right-coset coordinate translation back to the candidate fiber",
    )
    result_coset = None
    if inner.coset is not None:
        result_coset = RightCoset(
            inner.coset.subgroup,
            compose(representative, inner.coset.representative),
        )
    return ProofCarryingCoset(
        "exact_translated_" + inner.status,
        result_coset,
        inner.operation_kind,
        inner.root_n,
        inner.domain_size,
        inner.canonical,
        True,
        inner.local_cost_certified,
        inner.local_log2_cost_bound + extra_bound,
        inner.terminal_certified,
        inner.children,
        accounting,
        inner.permutation_candidates_checked,
        "exact subgroup SI on source composed with r^-1 was translated back to the original candidate right coset H*r",
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
    max_partition_states: int = 4096,
    max_depth: int = 64,
) -> ProofCarryingCoset:
    """Candidate-coset SI with proof-carrying structural recursion.

    Exact terminals are tried by represented group order first.  Intransitive H
    recurses over canonical orbits.  Large transitive H is classified: unique
    canonical imprimitive cases reuse V2 quotient/kernel recursion.  Primitive
    non-giant cases first try the certified small-ground Johnson terminal and then
    reuse rev177's validated complement-safe ground-profile terminal.  This closes
    larger Johnson grounds whenever the complete colored k-subset relation is
    determined by a bounded exact ground-profile partition, without enumerating
    the large represented Johnson group.

    The rev176 signed-ground small-order terminal is deliberately *not* repeated
    here: candidate SI has already run an exact small-order scan on the same
    subgroup with the same order gate, so invoking the signed copy would duplicate
    a solved/failed child rather than add coverage.  Remaining primitive non-giant,
    primitive giant and unresolved block-family cases stay typed fail-closed; no
    generic node-capped SI fallback is introduced.
    """
    H0 = candidate.subgroup
    n = H0.degree
    source = tuple(source_values)
    target = tuple(target_values)
    if len(source) != n or len(target) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")
    if max_partition_states < 1:
        raise ValueError("max_partition_states must be positive")

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
                "exact_empty_value_multiplicity", None, "value_multiplicity_terminal",
                root_n, n, True, True, True, local_bound, True, (), accounting, 0,
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
        classification = classify_s1_structure(
            H0,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
        )
        rinv = inverse(candidate.representative)
        subgroup_source = tuple(source[rinv[j]] for j in range(n))

        if classification.status == "canonical_imprimitive_block_system":
            from v2_imprimitive_small_image_v2 import imprimitive_small_image_string_isomorphism_v2_recursive

            inner = imprimitive_small_image_string_isomorphism_v2_recursive(
                H0,
                subgroup_source,
                target,
                root_n=root_n,
                polylog_power=polylog_power,
                max_explicit_degree=max_explicit_degree,
                quotient_order_poly_power=group_order_poly_power,
                max_quotient_image_order=max_group_order,
                candidate_group_order_poly_power=group_order_poly_power,
                max_candidate_group_order=max_group_order,
            )
            if inner.exact:
                return _translate_subgroup_si_back_to_candidate(inner, candidate.representative, degree=n)
            return _parent(
                root_n=root_n, degree=n, status=inner.status, coset=None,
                exact=False, children=(inner,), cost_certified=False,
                reason="unique canonical imprimitive candidate was structurally dispatched, but its V2 quotient/kernel child remains unresolved",
            )

        if classification.status == "primitive_non_giant":
            johnson = primitive_johnson_ground_string_isomorphism_terminal(
                H0,
                subgroup_source,
                target,
                root_n=root_n,
                polylog_power=polylog_power,
                max_ground_degree=max_explicit_degree,
            )
            if johnson.exact:
                return _translate_subgroup_si_back_to_candidate(johnson, candidate.representative, degree=n)

            profile = signed_johnson_ground_profile_partition_si(
                H0,
                subgroup_source,
                target,
                root_n=root_n,
                max_partition_states=min(max_partition_states, max(1, root_n ** 2)),
            )
            if profile.exact:
                return _translate_subgroup_si_back_to_candidate(
                    profile, candidate.representative, degree=n
                )

            return _parent(
                root_n=root_n, degree=n, status=profile.status, coset=None,
                exact=False, children=(johnson, profile), cost_certified=False,
                reason=(
                    "primitive non-giant candidate exhausted the certified small-ground Johnson terminal "
                    "and bounded complement-safe profile-partition terminal; a higher-order relational/"
                    "local-certificate Johnson recursion remains required"
                ),
            )

        status = classification.status
        if not status.startswith("undetermined_"):
            status = "undetermined_" + status
        return _parent(
            root_n=root_n,
            degree=n,
            status=status,
            coset=None,
            exact=False,
            children=(),
            cost_certified=False,
            reason=classification.reason,
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
            max_partition_states=max_partition_states,
            max_depth=max_depth,
        )
        children.append(child)
        if not child.exact:
            return _parent(
                root_n=root_n, degree=n, status=child.status, coset=None,
                exact=False, children=tuple(children), cost_certified=False,
                reason="candidate fiber reached an unresolved large-order structural orbit child; exact parent result withheld",
            )
        if child.coset is None:
            return _parent(
                root_n=root_n, degree=n, status="exact_empty_candidate_orbit_partition_v2",
                coset=None, exact=True, children=tuple(children),
                reason="one exact S1v2 subgroup-orbit child is empty, proving this candidate fiber empty",
            )

        lifted = orbit_action_preimage_coset(H, orbit, child.coset)
        if lifted.status != "exact_orbit_action_coset_preimage" or lifted.coset is None:
            return _parent(
                root_n=root_n, degree=n, status="undetermined_candidate_child_preimage_v2",
                coset=None, exact=False, children=tuple(children), cost_certified=False,
                reason="an exact S1v2 child could not be lifted through the subgroup orbit action",
            )
        H = lifted.subgroup
        r = compose(r, lifted.representative)

    return _parent(
        root_n=root_n, degree=n, status="exact_candidate_coset_string_isomorphism_v2",
        coset=RightCoset(H, r), exact=True, children=tuple(children),
        reason="all candidate-subgroup invariant orbit children were solved with S1v2 and exactly lifted; the returned coset is precisely the fiber string intersection",
    )
