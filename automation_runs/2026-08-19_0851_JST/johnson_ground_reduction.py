from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Tuple

from johnson_automorphism_action import analyze_johnson_automorphism_action


@dataclass(frozen=True)
class JohnsonGroundReduction:
    status: str
    ground_size: int
    subset_size: int
    quotient_size: int
    target_ambiguity_order: int
    complement_ambiguity: bool
    standard_colored_subsets: Tuple[Tuple[Tuple[int, ...], object], ...]
    reason: str


def reduce_johnson_colored_vertices(johnson_certificate, vertex_values) -> JohnsonGroundReduction:
    """Reduce a recognized Johnson quotient to its smaller hidden ground domain.

    rev119 provides a complete isomorphism coset from the canonically embedded
    pair-color graph to a standard J(v,k).  One representative transports the
    quotient-vertex values to standard k-subsets.  rev120 verifies that changing
    that representative by any target automorphism is exactly a permutation of
    the v ground points, plus the global subset-complement symmetry when v=2k.

    Thus this is an exact equivalence reduction, not an arbitrary coordinate
    choice: the residual coordinate ambiguity is recorded explicitly as the full
    Johnson automorphism group rather than discarded.
    """
    if johnson_certificate.status != "exact_johnson_color_relation":
        raise ValueError("an exact Johnson relation certificate is required")
    if johnson_certificate.isomorphism_coset is None:
        raise ValueError("Johnson certificate is missing its isomorphism coset")

    v = int(johnson_certificate.ground_size)
    k = int(johnson_certificate.subset_size)
    coset = johnson_certificate.isomorphism_coset
    representative = tuple(coset.representative)
    values = tuple(vertex_values)
    m = len(representative)
    if len(values) != m:
        raise ValueError("vertex-value count does not match Johnson quotient size")

    action = analyze_johnson_automorphism_action(coset.subgroup, v, k)
    if action.status != "exact_full_johnson_automorphism_action":
        raise AssertionError("target isomorphism ambiguity is not the full verified Johnson automorphism group")

    standard_values = [None] * m
    for source_vertex, target_vertex in enumerate(representative):
        if not (0 <= target_vertex < m) or standard_values[target_vertex] is not None:
            raise AssertionError("isomorphism representative is not a permutation")
        standard_values[target_vertex] = values[source_vertex]

    # Direct reversibility audit in the exact orientation used by rev111.
    if any(standard_values[representative[i]] != values[i] for i in range(m)):
        raise AssertionError("transport to standard Johnson coordinates is not reversible")

    standard_vertices = tuple(combinations(range(v), k))
    if len(standard_vertices) != m:
        raise AssertionError("C(v,k) does not match quotient size")

    return JohnsonGroundReduction(
        "exact_johnson_ground_reduction",
        v,
        k,
        m,
        coset.subgroup.order,
        v == 2 * k,
        tuple((S, standard_values[i]) for i, S in enumerate(standard_vertices)),
        "quotient values transported to standard k-subsets; all coordinate ambiguity is exactly ground S_v action plus middle-layer complement when applicable",
    )
