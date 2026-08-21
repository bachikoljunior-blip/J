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
from proof_carrying_state_orbit_candidate_v1 import exact_state_orbit_candidate_string_isomorphism
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from s1_string_isomorphism_v4 import s1_string_isomorphism_v4
from s1_structural_classifier_v1 import classify_s1_structure


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


def _candidate_coset_string_isomorphism_u2(
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
    max_state_orbit_work: int = 0,
) -> ProofCarryingCoset:
    """Candidate-coset SI with proof-carrying structural recursion.

    Exact terminals are tried by represented group order first.  Intransitive H
    recurses over canonical orbits.  Large transitive H is classified: unique
    canonical imprimitive cases reuse V2 quotient/kernel recursion; primitive
    non-giant cases try the certified small-ground J(v,2) special terminal;
    primitive giant and unresolved Johnson/block-family cases remain typed
    fail-closed, with no generic node-capped SI fallback.
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

    if max_state_orbit_work > 0:
        state_orbit = exact_state_orbit_candidate_string_isomorphism(
            candidate, source, target,
            root_n=root_n,
            max_work=max_state_orbit_work,
        )
        if state_orbit.exact:
            return state_orbit

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
            return _parent(
                root_n=root_n, degree=n, status=johnson.status, coset=None,
                exact=False, children=(johnson,), cost_certified=False,
                reason="primitive non-giant candidate reached the Johnson structural path but requires a larger/higher-arity relational ground recursion",
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
        child = s1_string_isomorphism_v4(
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
    max_state_orbit_work: int = 0,
    proof_identity=None,
) -> ProofCarryingCoset:
    """Run u2 and attach an optional execution identity before returning."""
    proof = _candidate_coset_string_isomorphism_u2(
        candidate,
        source_values,
        target_values,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
        max_state_orbit_work=max_state_orbit_work,
    )
    if proof_identity is None:
        return proof
    if proof.proof_identity is not None and proof.proof_identity != proof_identity:
        raise ValueError("candidate proof already carries a different execution identity")
    return replace(proof, proof_identity=proof_identity)
