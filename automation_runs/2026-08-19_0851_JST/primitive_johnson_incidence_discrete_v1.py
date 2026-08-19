from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import log2

from canonical_orbital_size_relation import canonical_orbital_size_relation
from coset_stabilizer_primitives import RightCoset
from johnson_pair_relation_recognizer import recognize_johnson_pair_relation
from permutation_group_schreier import identity, schreier_stabilizer_chain
from primitive_johnson_ground_terminal_v1 import _induced_subset_permutation
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class JohnsonIncidenceDiscreteProof(ProofCarryingCoset):
    johnson_ground_size: int = 0
    johnson_subset_size: int = 0
    recognition_search_nodes: int = 0
    ground_signature_classes: int = 0


def _frozen_counter(values):
    return frozenset(Counter(values).items())


def _std_values(values, coordinate):
    out = [None] * len(coordinate)
    for original, standard_index in enumerate(coordinate):
        out[standard_index] = values[original]
    return tuple(out)


def _vertex_incidence_signatures(std_values, standard_subsets, ground_size):
    incident = [[] for _ in range(ground_size)]
    for index, subset in enumerate(standard_subsets):
        value = std_values[index]
        for x in subset:
            incident[x].append(value)
    return tuple(_frozen_counter(items) for items in incident)


def primitive_johnson_incidence_discrete_terminal(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
    max_recognition_nodes: int = 500000,
) -> JohnsonIncidenceDiscreteProof:
    """Exact large-ground Johnson SI when incidence signatures individualize it.

    After a certified J(v,k) coordinate embedding, each ground point receives the
    multiset of string colors on represented k-subsets containing that point.
    This is a functorial/canonical vertex coloring of the Johnson ground.  When
    these signatures are discrete in both strings, every Johnson-induced
    isomorphism is forced to one ground permutation.  We induce that unique
    permutation back to the original C(v,k)-point domain, filter it by exact
    ambient-group membership, and verify the full strings.

    The exceptional v=2k family is left fail-closed here because the complement
    automorphism is not represented by a ground-point permutation.  The small
    ground terminal handles it exactly by scanning both Johnson automorphism
    cosets; larger v=2k requires the general relational recursion.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if len(source) != m or len(target) != m:
        raise ValueError("string/group degree mismatch")
    if root_n < m or root_n <= 0 or max_recognition_nodes < 1:
        raise ValueError("invalid incidence terminal parameters")
    try:
        if Counter(source) != Counter(target):
            local = 8.0 * log2(max(2, m)) + 12.0
            accounting = RecurrenceAccountingNode(
                n=root_n, m=max(1, m), operation_kind="value_multiplicity_terminal",
                canonical=True, cost_certified=True, local_log2_cost_bound=local,
                children=(), terminal_certified=True,
                reason="global source/target relation-color multiplicities differ",
            )
            return JohnsonIncidenceDiscreteProof(
                "exact_empty_johnson_value_multiplicity", None,
                "value_multiplicity_terminal", root_n, m, True, True, True,
                local, True, (), accounting, 0,
                "global relation-color multiplicity mismatch proves emptiness",
            )
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc

    relation = canonical_orbital_size_relation(group)
    johnson = recognize_johnson_pair_relation(
        m, relation.pair_weights, max_nodes_per_candidate=max_recognition_nodes
    )
    if johnson.status != "exact_johnson_color_relation" or johnson.isomorphism_coset is None:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, m), operation_kind="primitive_johnson_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False, reason=johnson.reason,
        )
        return JohnsonIncidenceDiscreteProof(
            "undetermined_primitive_non_giant_not_johnson", None,
            "primitive_johnson_unresolved", root_n, m, True, False, False,
            0.0, False, (), accounting, 0, johnson.reason,
            johnson_ground_size=int(johnson.ground_size or 0),
            johnson_subset_size=int(johnson.subset_size or 0),
            recognition_search_nodes=johnson.search_nodes,
            ground_signature_classes=0,
        )

    v = int(johnson.ground_size)
    k = int(johnson.subset_size)
    if v == 2 * k:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, m), operation_kind="primitive_johnson_relational_recursion",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="v=2k has the extra Johnson complement automorphism; discrete ground-point signatures alone are not a complete coordinate invariant",
        )
        return JohnsonIncidenceDiscreteProof(
            "undetermined_johnson_complement_family", None,
            "primitive_johnson_relational_recursion", root_n, m, True, False,
            False, 0.0, False, (), accounting, 0,
            "large self-complementary Johnson ground requires a relation-level recursion that carries the complement coset",
            johnson_ground_size=v, johnson_subset_size=k,
            recognition_search_nodes=johnson.search_nodes,
            ground_signature_classes=0,
        )

    coordinate = tuple(johnson.isomorphism_coset.representative)
    standard_subsets = tuple(combinations(range(v), k))
    if len(standard_subsets) != m or sorted(coordinate) != list(range(m)):
        raise AssertionError("invalid Johnson coordinate certificate")
    source_std = _std_values(source, coordinate)
    target_std = _std_values(target, coordinate)
    source_sig = _vertex_incidence_signatures(source_std, standard_subsets, v)
    target_sig = _vertex_incidence_signatures(target_std, standard_subsets, v)

    if Counter(source_sig) != Counter(target_sig):
        work = max(1, johnson.search_nodes + m * max(1, k))
        local = log2(work) + 14.0 * log2(max(2, m)) + 28.0
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, m), operation_kind="johnson_incidence_signature_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local,
            children=(), terminal_certified=True,
            reason="canonical Johnson-ground incidence-signature multisets differ",
        )
        return JohnsonIncidenceDiscreteProof(
            "exact_empty_johnson_incidence_signature", None,
            "johnson_incidence_signature_terminal", root_n, m, True, True,
            True, local, True, (), accounting, 0,
            "different canonical ground incidence-signature multisets rule out every Johnson-induced ambient isomorphism",
            johnson_ground_size=v, johnson_subset_size=k,
            recognition_search_nodes=johnson.search_nodes,
            ground_signature_classes=len(set(source_sig)),
        )

    if len(set(source_sig)) != v or len(set(target_sig)) != v:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, m), operation_kind="primitive_johnson_relational_recursion",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="Johnson ground incidence signatures are canonical but not discrete; their color classes must drive a relation-level recursive restriction",
        )
        return JohnsonIncidenceDiscreteProof(
            "undetermined_johnson_incidence_not_discrete", None,
            "primitive_johnson_relational_recursion", root_n, m, True, False,
            False, 0.0, False, (), accounting, 0,
            "the incidence coloring exposes a canonical ground partition but not yet a unique ground isomorphism",
            johnson_ground_size=v, johnson_subset_size=k,
            recognition_search_nodes=johnson.search_nodes,
            ground_signature_classes=len(set(source_sig)),
        )

    target_position = {signature: y for y, signature in enumerate(target_sig)}
    sigma = tuple(target_position[signature] for signature in source_sig)
    q = _induced_subset_permutation(coordinate, sigma, v, k, complement=False)
    valid = group.contains(q) and all(source[i] == target[q[i]] for i in range(m))
    work = max(1, johnson.search_nodes + m * max(1, k) + v)
    local = log2(work) + 16.0 * log2(max(2, m)) + 32.0
    accounting = RecurrenceAccountingNode(
        n=root_n, m=max(1, m), operation_kind="johnson_incidence_signature_terminal",
        canonical=True, cost_certified=True, local_log2_cost_bound=local,
        children=(), terminal_certified=True,
        reason="discrete canonical Johnson-ground incidence signatures force one ground permutation, followed by exact ambient membership and full relation verification",
    )
    if not valid:
        return JohnsonIncidenceDiscreteProof(
            "exact_empty_johnson_incidence_unique_candidate", None,
            "johnson_incidence_signature_terminal", root_n, m, True, True,
            True, local, True, (), accounting, 1,
            "the uniquely forced ground permutation is not an ambient string isomorphism, so no solution exists",
            johnson_ground_size=v, johnson_subset_size=k,
            recognition_search_nodes=johnson.search_nodes,
            ground_signature_classes=v,
        )

    singleton = schreier_stabilizer_chain([identity(m)])
    result = RightCoset(singleton, q)
    if not result.contains(q):
        raise AssertionError("singleton Johnson incidence coset reconstruction failed")
    return JohnsonIncidenceDiscreteProof(
        "exact_johnson_incidence_discrete_coset", result,
        "johnson_incidence_signature_terminal", root_n, m, True, True, True,
        local, True, (), accounting, 1,
        "discrete canonical incidence signatures force the unique exact SI witness",
        johnson_ground_size=v, johnson_subset_size=k,
        recognition_search_nodes=johnson.search_nodes,
        ground_signature_classes=v,
    )
