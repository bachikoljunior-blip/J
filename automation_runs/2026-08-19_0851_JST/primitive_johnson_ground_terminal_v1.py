from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations
from math import factorial, log2

from canonical_orbital_size_relation import canonical_orbital_size_relation
from coset_stabilizer_primitives import RightCoset
from johnson_pair_relation_recognizer import recognize_johnson_pair_relation
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class PrimitiveJohnsonGroundProof(ProofCarryingCoset):
    johnson_ground_size: int = 0
    johnson_subset_size: int = 0
    ground_permutations_checked: int = 0
    recognition_search_nodes: int = 0


def _induced_subset_permutation(coordinate, ground_perm, ground_size, subset_size, *, complement=False):
    standard = tuple(combinations(range(ground_size), subset_size))
    index = {subset: i for i, subset in enumerate(standard)}
    cinv = [0] * len(coordinate)
    for original, standard_index in enumerate(coordinate):
        cinv[standard_index] = original
    universe = set(range(ground_size))
    out = []
    for original in range(len(coordinate)):
        subset = standard[coordinate[original]]
        moved = tuple(sorted(ground_perm[x] for x in subset))
        if complement:
            moved = tuple(sorted(universe.difference(moved)))
        out.append(cinv[index[moved]])
    return tuple(out)


def primitive_johnson_ground_string_isomorphism_terminal(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_ground_degree: int = 8,
    max_recognition_nodes: int = 500000,
) -> PrimitiveJohnsonGroundProof:
    """Exact SI terminal for a certified J(v,k) action with small ground v.

    A canonical orbital-size color is recognized against J(v,k), giving a full
    coordinate-isomorphism coset from the current m=C(v,k) points to standard
    k-subsets.  We enumerate the complete automorphism family of the Johnson
    graph on the smaller ground: induced S_v, plus the complement coset when
    v=2k.  Every induced current-domain permutation is then filtered by exact
    membership in the supplied ambient group and tested on the two strings.

    Therefore coordinate-representative ambiguity is harmless: changing Johnson
    coordinates composes with a Johnson automorphism, and the complete Johnson
    automorphism family is enumerated before ambient membership filtering.  This
    is an exact special terminal only when v lies inside the explicit/polylog
    window; larger grounds fail closed for recursive relational treatment.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if len(source) != m or len(target) != m:
        raise ValueError("string/group degree mismatch")
    if root_n < m or root_n <= 0:
        raise ValueError("root_n must dominate the current degree")
    if polylog_power < 1 or max_ground_degree < 1 or max_recognition_nodes < 1:
        raise ValueError("invalid Johnson terminal parameters")

    relation = canonical_orbital_size_relation(group)
    johnson = recognize_johnson_pair_relation(
        m,
        relation.pair_weights,
        max_nodes_per_candidate=max_recognition_nodes,
    )
    if johnson.status != "exact_johnson_color_relation" or johnson.isomorphism_coset is None:
        reason = (
            "canonical orbital-size relation did not yield a certified Johnson coordinate system"
            if not johnson.status.startswith("undetermined")
            else johnson.reason
        )
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, m), operation_kind="primitive_johnson_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False, reason=reason,
        )
        return PrimitiveJohnsonGroundProof(
            "undetermined_primitive_non_giant_not_johnson", None,
            "primitive_johnson_unresolved", root_n, m, True, False, False, 0.0,
            False, (), accounting, 0, reason,
            johnson_ground_size=int(johnson.ground_size or 0),
            johnson_subset_size=int(johnson.subset_size or 0),
            ground_permutations_checked=0,
            recognition_search_nodes=johnson.search_nodes,
        )

    v = int(johnson.ground_size)
    k = int(johnson.subset_size)
    threshold = max(1.0, log2(max(2, root_n)) ** polylog_power)
    if v > max_ground_degree or v > threshold + 1e-12:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, m), operation_kind="primitive_johnson_ground_cap",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="Johnson ground is larger than the explicit/polylog terminal window",
        )
        return PrimitiveJohnsonGroundProof(
            "undetermined_johnson_ground_cap", None,
            "primitive_johnson_ground_cap", root_n, m, True, False, False, 0.0,
            False, (), accounting, 0,
            "the Johnson structure is certified, but its ground domain must recurse rather than be brute-forced",
            johnson_ground_size=v, johnson_subset_size=k,
            ground_permutations_checked=0,
            recognition_search_nodes=johnson.search_nodes,
        )

    coordinate = tuple(johnson.isomorphism_coset.representative)
    if sorted(coordinate) != list(range(m)):
        raise AssertionError("Johnson coordinate representative is not a permutation")

    matches = []
    ground_checked = 0
    complement_modes = (False, True) if v == 2 * k else (False,)
    for sigma in permutations(range(v)):
        for use_complement in complement_modes:
            ground_checked += 1
            q = _induced_subset_permutation(
                coordinate, sigma, v, k, complement=use_complement
            )
            if not group.contains(q):
                continue
            if all(source[i] == target[q[i]] for i in range(m)):
                matches.append(q)

    execution_units = max(1, johnson.search_nodes + ground_checked)
    local_bound = log2(execution_units) + 18.0 * log2(max(2, m)) + 38.0
    expected_automorphisms_scanned = factorial(v) * len(complement_modes)
    if ground_checked != expected_automorphisms_scanned:
        raise AssertionError("incomplete Johnson automorphism enumeration")
    if local_bound + 1e-12 < log2(max(1, expected_automorphisms_scanned)):
        raise AssertionError("Johnson terminal charge does not dominate automorphism enumeration")

    if not matches:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, m), operation_kind="primitive_johnson_ground_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=True,
            reason="certified J(v,k) coordinates; complete small-ground Johnson automorphism scan filtered by exact ambient membership found no SI witness",
        )
        return PrimitiveJohnsonGroundProof(
            "exact_empty_primitive_johnson_ground", None,
            "primitive_johnson_ground_terminal", root_n, m, True, True, True,
            local_bound, True, (), accounting, ground_checked,
            "every induced Johnson automorphism was ambient-membership filtered and string-tested",
            johnson_ground_size=v, johnson_subset_size=k,
            ground_permutations_checked=ground_checked,
            recognition_search_nodes=johnson.search_nodes,
        )

    witness = min(matches)
    translated = tuple(compose(inverse(witness), p) for p in matches)
    subgroup = schreier_stabilizer_chain(translated or (identity(m),))
    result = RightCoset(subgroup, witness)
    if subgroup.order != len(matches):
        raise AssertionError("Johnson terminal matches did not reconstruct the expected subgroup order")
    if any(not result.contains(p) for p in matches):
        raise AssertionError("Johnson terminal reconstructed coset lost an exact match")

    accounting = RecurrenceAccountingNode(
        n=root_n, m=max(1, m), operation_kind="primitive_johnson_ground_terminal",
        canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
        children=(), terminal_certified=True,
        reason="certified J(v,k) coordinates; complete small-ground Johnson automorphism enumeration and exact coset reconstruction",
    )
    return PrimitiveJohnsonGroundProof(
        "exact_primitive_johnson_ground_coset", result,
        "primitive_johnson_ground_terminal", root_n, m, True, True, True,
        local_bound, True, (), accounting, ground_checked,
        "the complete SI subset inside the represented primitive Johnson action was reconstructed as one right coset",
        johnson_ground_size=v, johnson_subset_size=k,
        ground_permutations_checked=ground_checked,
        recognition_search_nodes=johnson.search_nodes,
    )
