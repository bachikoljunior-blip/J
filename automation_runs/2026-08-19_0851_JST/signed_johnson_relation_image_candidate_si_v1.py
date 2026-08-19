from __future__ import annotations

from dataclasses import replace
from math import log2

from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from signed_johnson_complement_safe_image_si_v1 import (
    signed_johnson_complement_safe_relation_image_si,
)
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


def _absorb_filter_cost(exact_child: ProofCarryingCoset, relation_filter: ProofCarryingCoset):
    if not exact_child.exact:
        raise ValueError("only an exact candidate child can close the full string restriction")
    if not relation_filter.local_cost_certified:
        raise ValueError("relation filter cost must be certified before composition")
    extra = relation_filter.local_log2_cost_bound + 8.0 * log2(max(2, exact_child.domain_size)) + 16.0
    accounting = replace(
        exact_child.accounting,
        local_log2_cost_bound=exact_child.accounting.local_log2_cost_bound + extra,
        reason=(
            exact_child.accounting.reason
            + "; preceded by exact complement-safe signed-Johnson relation-image SI and rev179 original-domain preimage filtering"
        ),
    )
    return ProofCarryingCoset(
        "exact_w1r_relation_image_candidate_" + exact_child.status,
        exact_child.coset,
        exact_child.operation_kind,
        exact_child.root_n,
        exact_child.domain_size,
        exact_child.canonical,
        True,
        bool(exact_child.local_cost_certified),
        exact_child.local_log2_cost_bound + extra,
        exact_child.terminal_certified,
        exact_child.children,
        accounting,
        exact_child.permutation_candidates_checked + relation_filter.permutation_candidates_checked,
        (
            "W1R-H composition: a canonical strictly smaller relation image was solved exactly, its right coset was lifted "
            "to the original Johnson domain, and the remaining full colored k-subset string was solved exactly inside that candidate"
        ),
    )


def signed_johnson_relation_image_candidate_string_isomorphism(
    group,
    source_values,
    target_values,
    *,
    relation_arity: int = 2,
    root_n: int | None = None,
    max_recognition_nodes: int = 500000,
    image_si_poly_power: int = 4,
    max_image_si_nodes: int = 200000,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
    max_depth: int = 64,
):
    """W1R-H closure: exact smaller relation image, then exact full-string candidate recursion.

    The first stage is rev180's complement-safe t-local image SI.  A nonempty
    result is the complete original-domain preimage of the exact image relation
    coset, hence every true full-string isomorphism lies inside it.  The existing
    U2/S1/V2 candidate machinery is then applied to that candidate instead of to
    the original ambient group.  This can turn a hard primitive Johnson ambient
    action into a small-order, intransitive, imprimitive, or already-supported
    Johnson candidate subgroup without enumerating the represented ambient group.

    If the candidate machinery still reaches a hard transitive primitive child,
    the exact relation coset is retained as verified structural progress but no
    full-string or quasipolynomial closure is claimed.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    if root_n < n:
        raise ValueError("root_n must dominate the current domain")

    relation = signed_johnson_complement_safe_relation_image_si(
        group,
        source,
        target,
        relation_arity=relation_arity,
        root_n=root_n,
        max_recognition_nodes=max_recognition_nodes,
        image_si_poly_power=image_si_poly_power,
        max_image_si_nodes=max_image_si_nodes,
    )
    if relation.exact:
        return relation
    if relation.coset is None:
        return relation

    candidate = candidate_coset_string_isomorphism_u2(
        relation.coset,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=candidate_group_order_poly_power,
        max_group_order=max_candidate_group_order,
        max_depth=max_depth,
    )
    if candidate.exact:
        return _absorb_filter_cost(candidate, relation)

    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="unresolved_signed_johnson_relation_candidate",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=(),
        terminal_certified=False,
        reason=(
            "the strictly smaller relation image and complete original-domain preimage are certified, but the remaining "
            "full colored k-subset restriction is still a hard candidate-coset child"
        ),
    )
    return ProofCarryingCoset(
        "undetermined_w1r_after_relation_image_" + candidate.status,
        relation.coset,
        "unresolved_signed_johnson_relation_candidate",
        root_n,
        n,
        True,
        False,
        False,
        0.0,
        False,
        (relation, candidate),
        accounting,
        relation.permutation_candidates_checked + candidate.permutation_candidates_checked,
        (
            "rev180/rev179 reduced the ambient search to an exact relation-preserving candidate coset; "
            "existing U2/S1/V2 candidate recursion did not yet certify the full string intersection: " + candidate.reason
        ),
    )
