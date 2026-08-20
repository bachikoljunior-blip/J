from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import ceil, comb, log
from typing import Iterable


@dataclass(frozen=True)
class UniformNeighborhoodHypergraph:
    status: str
    left_vertices: tuple[int, ...]
    right_size: int
    original_degree: int
    normalized_degree: int
    complemented: bool
    hyperedges: tuple[tuple[int, ...], ...]
    complete_uniform_hypergraph: bool
    johnson_embedding: tuple[tuple[int, tuple[int, ...]], ...]
    test_arity: int | None
    test_coordinates: tuple[tuple[int, ...], ...]
    test_colors: tuple[int, ...]
    test_relation_nonconstant: bool
    exact: bool
    reason: str


def build_uniform_neighborhood_hypergraph(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    selected_left: Iterable[int],
) -> UniformNeighborhoodHypergraph:
    """Build the exact uniform-neighborhood hypergraph used in Prop. 5.7.

    The selected left vertices must have one common positive non-full degree and
    pairwise distinct neighborhoods. If that degree exceeds half the right part,
    all neighborhoods are complemented; this preserves distinctness and the
    induced isomorphism problem while reducing the uniformity.

    If every normalized d-subset occurs exactly once, the selected left vertices
    are explicitly labeled by all d-subsets of V2: this is the complete Johnson
    ground case. Otherwise an exact controlled-arity relation on V2 is produced by
    coloring each t-subset by the number of hyperedges containing it, using the
    same arity choice appearing in the Proposition-5.7 proof when it is meaningful.
    If that relation is still constant, the routine fails closed rather than using
    the asymptotic design argument as if it had been mechanically proved here.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 1 or n2 < 2:
        raise ValueError("uniform-neighborhood stage requires a positive left part and right_size>=2")
    chosen = tuple(sorted(set(int(x) for x in selected_left)))
    if not chosen or any(not 0 <= x < n1 for x in chosen):
        raise ValueError("selected_left must be a nonempty subset of the left part")

    nbrs = [set() for _ in range(n1)]
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < n1 or not 0 <= b < n2:
            raise ValueError("bipartite edge endpoint outside the declared part")
        nbrs[a].add(b)
    degrees = {len(nbrs[a]) for a in chosen}
    if len(degrees) != 1:
        return UniformNeighborhoodHypergraph(
            "uniform_neighborhood_degree_mismatch", chosen, n2, -1, -1, False,
            (), False, (), None, (), (), False, True,
            "selected left vertices do not have one common neighborhood size",
        )
    degree = degrees.pop()
    if not 0 < degree < n2:
        return UniformNeighborhoodHypergraph(
            "uniform_neighborhood_trivial_degree", chosen, n2, degree, degree, False,
            (), False, (), None, (), (), False, True,
            "the common neighborhood degree is empty or full and cannot supply the nontrivial hypergraph stage",
        )

    raw = [tuple(sorted(nbrs[a])) for a in chosen]
    if len(set(raw)) != len(raw):
        return UniformNeighborhoodHypergraph(
            "uniform_neighborhood_left_twins_present", chosen, n2, degree, degree, False,
            tuple(raw), False, (), None, (), (), False, True,
            "selected left vertices still contain identical full neighborhoods",
        )

    complemented = degree > n2 / 2
    if complemented:
        universe = set(range(n2))
        normalized = [tuple(sorted(universe - set(S))) for S in raw]
        d = n2 - degree
    else:
        normalized = raw
        d = degree
    hyperedges = tuple(normalized)
    if len(set(hyperedges)) != len(hyperedges):
        raise AssertionError("bipartite complementation unexpectedly merged distinct neighborhoods")

    complete = len(hyperedges) == comb(n2, d) and set(hyperedges) == set(combinations(range(n2), d))
    if complete:
        embedding = tuple((a, S) for a, S in zip(chosen, hyperedges))
        return UniformNeighborhoodHypergraph(
            "certified_complete_uniform_neighborhood_johnson_embedding",
            chosen, n2, degree, d, complemented, hyperedges, True, embedding,
            None, (), (), False, True,
            "distinct normalized neighborhoods are exactly all d-subsets of the right ground, giving an explicit Johnson labeling",
        )

    m = len(chosen)
    ratio = log(max(2, m)) / log(max(2, n2))
    cap = max(1, 6 * ceil(ratio))
    t = min(d, cap)
    coords = tuple(combinations(range(n2), t))
    edge_sets = tuple(set(S) for S in hyperedges)
    colors = tuple(sum(set(T).issubset(S) for S in edge_sets) for T in coords)
    nonconstant = len(set(colors)) > 1
    return UniformNeighborhoodHypergraph(
        "certified_nonconstant_uniform_neighborhood_test_relation" if nonconstant else "uniform_neighborhood_test_relation_constant_unresolved",
        chosen, n2, degree, d, complemented, hyperedges, False, (),
        t, coords, colors, nonconstant, True,
        (
            "the exact controlled-arity containment-count relation on the right ground is nonconstant"
            if nonconstant
            else "the mechanically constructed containment-count relation is constant; a separate design-bound proof is required before descending"
        ),
    )
