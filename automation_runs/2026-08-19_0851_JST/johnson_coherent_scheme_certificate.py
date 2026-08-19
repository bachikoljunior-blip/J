from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Tuple


@dataclass(frozen=True)
class JohnsonCoherentSchemeCertificate:
    status: str
    ground_size: int
    subset_size: int
    quotient_size: int
    coherent_rank: int
    expected_johnson_rank: int
    distance_to_color: Tuple[Tuple[int, int], ...]
    exact_distance_scheme: bool
    reason: str


def certify_johnson_coherent_scheme(coherent_certificate, johnson_certificate) -> JohnsonCoherentSchemeCertificate:
    """Verify the full stable pair relation against Johnson distance classes.

    rev119 supplies an exact isomorphism from the quotient points to standard
    k-subsets of a v-set. Any alternative representative differs by a Johnson
    automorphism and therefore preserves Johnson distance, so using one coset
    representative here does not introduce a hidden coordinate assumption.

    The certificate is exact when each distance d=0..k has one coherent color and
    different distances have different colors. A strictly finer coherent relation
    is reported honestly rather than being collapsed to the Johnson scheme.
    """
    if johnson_certificate.status != "exact_johnson_color_relation":
        raise ValueError("exact Johnson relation certificate required")
    if johnson_certificate.isomorphism_coset is None:
        raise ValueError("Johnson certificate is missing isomorphism coset")
    if coherent_certificate.status == "undetermined_round_limit":
        raise ValueError("coherent refinement is undetermined")

    v = int(johnson_certificate.ground_size)
    k = int(johnson_certificate.subset_size)
    p = tuple(johnson_certificate.isomorphism_coset.representative)
    colors = tuple(tuple(row) for row in coherent_certificate.pair_color_matrix)
    m = len(p)
    if coherent_certificate.quotient_size != m or len(colors) != m or any(len(row) != m for row in colors):
        raise ValueError("coherent/Johnson quotient-size mismatch")

    standard_vertices = tuple(combinations(range(v), k))
    if len(standard_vertices) != m:
        raise AssertionError("C(v,k) mismatch")
    standard_sets = tuple(set(S) for S in standard_vertices)

    distance_colors = {d: set() for d in range(k + 1)}
    for u in range(m):
        for w in range(m):
            d = k - len(standard_sets[p[u]] & standard_sets[p[w]])
            distance_colors[d].add(colors[u][w])

    single = all(len(cs) == 1 for cs in distance_colors.values())
    mapping = tuple((d, next(iter(distance_colors[d]))) for d in range(k + 1) if len(distance_colors[d]) == 1)
    distinct = single and len({color for _, color in mapping}) == k + 1
    exact = distinct and coherent_certificate.rank == k + 1

    return JohnsonCoherentSchemeCertificate(
        "exact_johnson_distance_scheme" if exact else "johnson_graph_with_refined_coherent_structure",
        v,
        k,
        m,
        coherent_certificate.rank,
        k + 1,
        mapping,
        exact,
        "coherent ordered-pair colors compared exactly with Johnson intersection-distance classes through the verified isomorphism coset",
    )
