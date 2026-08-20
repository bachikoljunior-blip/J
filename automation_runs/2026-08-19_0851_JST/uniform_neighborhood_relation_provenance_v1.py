from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

Subset = tuple[int, ...]
RelationInventory = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class UniformNeighborhoodRelation:
    status: str
    left_size: int
    right_size: int
    original_common_degree: int | None
    normalized_degree: int | None
    complemented: bool
    neighborhoods: tuple[Subset, ...]
    relation_arity: int | None
    relation_classes: tuple[tuple[int, tuple[Subset, ...]], ...]
    relation_inventory: RelationInventory
    johnson_embedding: tuple[tuple[int, Subset], ...]
    exact: bool
    reason: str


@dataclass(frozen=True)
class PairedUniformNeighborhoodProvenance:
    status: str
    source: UniformNeighborhoodRelation
    target: UniformNeighborhoodRelation
    paired_outcome: str | None
    relation_inventory: RelationInventory
    provenance_verified: bool
    exact: bool
    reason: str


def _normalize_edges(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("edge endpoint outside the declared bipartite parts")
        out.add((a, b))
    return out


def _empty(
    status: str,
    n1: int,
    n2: int,
    reason: str,
    *,
    degree: int | None = None,
) -> UniformNeighborhoodRelation:
    return UniformNeighborhoodRelation(
        status,
        n1,
        n2,
        degree,
        None,
        False,
        (),
        None,
        (),
        (),
        (),
        True,
        reason,
    )


def derive_uniform_neighborhood_relation(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    *,
    max_subsets: int = 200000,
) -> UniformNeighborhoodRelation:
    """Construct the exact uniform-neighborhood Johnson/relation alternative.

    The left neighborhoods form a hypergraph on the right ground.  The routine
    requires a nontrivial uniform degree and pairwise distinct neighborhoods, and
    complements every neighborhood when the common degree exceeds half the right
    ground.  If the resulting family is the complete uniform hypergraph, the left
    vertices receive an explicit Johnson coordinate.  Otherwise the symmetric
    containment-count relation from Proposition 5.7 is materialized on t-subsets,
    where ``t=min(d, 6*ceil(log_{|V2|} |V1|))``.

    The implementation certifies only the finite exact structural object.  It does
    not import the asymptotic Design Lemma contradiction, canonical ambient group
    cost, or recursive isomorphism-set closure.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 2 or n2 < 3:
        raise ValueError("uniform-neighborhood provenance requires left_size>=2 and right_size>=3")
    if max_subsets < 1:
        raise ValueError("max_subsets must be positive")

    edge_set = _normalize_edges(n1, n2, edges)
    nbrs = [set() for _ in range(n1)]
    for a, b in edge_set:
        nbrs[a].add(b)
    degrees = tuple(len(N) for N in nbrs)
    if len(set(degrees)) != 1:
        return _empty(
            "uniform_neighborhood_requires_common_left_degree",
            n1,
            n2,
            "left neighborhoods do not have one exact common degree",
        )
    original_degree = degrees[0]
    if not 0 < original_degree < n2:
        return _empty(
            "uniform_neighborhood_requires_nontrivial_degree",
            n1,
            n2,
            "the common left degree must be strictly between 0 and |V2|",
            degree=original_degree,
        )

    complemented = original_degree > n2 / 2
    if complemented:
        ground = set(range(n2))
        normalized = [ground - N for N in nbrs]
    else:
        normalized = nbrs
    normalized_degree = len(normalized[0])
    neighborhoods = tuple(tuple(sorted(N)) for N in normalized)
    if len(set(neighborhoods)) != n1:
        return UniformNeighborhoodRelation(
            "uniform_neighborhood_requires_twin_free_left",
            n1,
            n2,
            original_degree,
            normalized_degree,
            complemented,
            neighborhoods,
            None,
            (),
            (),
            (),
            True,
            "two left vertices have the same normalized neighborhood",
        )

    complete_size = math.comb(n2, normalized_degree)
    if n1 == complete_size and set(neighborhoods) == set(combinations(range(n2), normalized_degree)):
        embedding = tuple((a, neighborhoods[a]) for a in range(n1))
        return UniformNeighborhoodRelation(
            "explicit_johnson_embedding",
            n1,
            n2,
            original_degree,
            normalized_degree,
            complemented,
            neighborhoods,
            normalized_degree,
            ((1, tuple(sorted(neighborhoods))),),
            ((1, n1),),
            embedding,
            True,
            "the normalized neighborhood hypergraph is the complete uniform family; each left vertex is explicitly identified with its right-ground subset",
        )

    ell = math.log(n1) / math.log(n2)
    theorem_cap = max(1, 6 * math.ceil(ell))
    relation_arity = min(normalized_degree, theorem_cap)
    subset_count = math.comb(n2, relation_arity)
    if subset_count > max_subsets:
        return UniformNeighborhoodRelation(
            "undetermined_containment_relation_subset_limit",
            n1,
            n2,
            original_degree,
            normalized_degree,
            complemented,
            neighborhoods,
            relation_arity,
            (),
            (),
            (),
            True,
            f"materializing C(|V2|,t)={subset_count} subsets exceeds max_subsets={max_subsets}",
        )

    neighborhood_sets = tuple(frozenset(N) for N in neighborhoods)
    buckets: dict[int, list[Subset]] = defaultdict(list)
    for subset in combinations(range(n2), relation_arity):
        S = frozenset(subset)
        count = sum(S <= edge for edge in neighborhood_sets)
        buckets[count].append(subset)
    classes = tuple((count, tuple(buckets[count])) for count in sorted(buckets))
    inventory = tuple((count, len(buckets[count])) for count in sorted(buckets))
    if len(classes) == 1:
        return UniformNeighborhoodRelation(
            "homogeneous_containment_design_residual",
            n1,
            n2,
            original_degree,
            normalized_degree,
            complemented,
            neighborhoods,
            relation_arity,
            classes,
            inventory,
            (),
            True,
            "the exact theorem-arity containment count is constant; a separately certified Design bound/recursion is required",
        )

    return UniformNeighborhoodRelation(
        "nonconstant_containment_relation",
        n1,
        n2,
        original_degree,
        normalized_degree,
        complemented,
        neighborhoods,
        relation_arity,
        classes,
        inventory,
        (),
        True,
        "the exact symmetric containment-count relation on the right ground is nonconstant and proof-carrying",
    )


def certify_paired_uniform_neighborhood_provenance(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    max_subsets: int = 200000,
) -> PairedUniformNeighborhoodProvenance:
    """Pair the exact Johnson or containment-relation outcome across two inputs."""
    src = derive_uniform_neighborhood_relation(
        left_size, right_size, tuple(source_edges), max_subsets=max_subsets
    )
    dst = derive_uniform_neighborhood_relation(
        left_size, right_size, tuple(target_edges), max_subsets=max_subsets
    )
    empty: RelationInventory = ()
    if src.status != dst.status:
        return PairedUniformNeighborhoodProvenance(
            "paired_uniform_outcome_mismatch",
            src,
            dst,
            None,
            empty,
            False,
            True,
            "a right-ground isomorphism must preserve the exact normalized uniform-neighborhood outcome type",
        )
    if (
        src.original_common_degree,
        src.normalized_degree,
        src.complemented,
        src.relation_arity,
        src.relation_inventory,
    ) != (
        dst.original_common_degree,
        dst.normalized_degree,
        dst.complemented,
        dst.relation_arity,
        dst.relation_inventory,
    ):
        return PairedUniformNeighborhoodProvenance(
            "paired_uniform_relation_inventory_mismatch",
            src,
            dst,
            None,
            empty,
            False,
            True,
            "a right-ground isomorphism must preserve degree normalization, theorem arity, and every containment-count multiplicity",
        )

    if src.status == "explicit_johnson_embedding":
        return PairedUniformNeighborhoodProvenance(
            "paired_explicit_johnson_provenance",
            src,
            dst,
            "johnson",
            src.relation_inventory,
            True,
            True,
            "both sides are explicitly coordinated by the complete normalized uniform family; ambient ground-set transporter remains unresolved",
        )
    if src.status == "nonconstant_containment_relation":
        return PairedUniformNeighborhoodProvenance(
            "paired_nonconstant_containment_relation_provenance",
            src,
            dst,
            "relation",
            src.relation_inventory,
            True,
            True,
            "every right-ground isomorphism preserves the integer containment-count relation; exact relation transporter remains unresolved",
        )
    return PairedUniformNeighborhoodProvenance(
        "paired_uniform_neighborhood_no_progress",
        src,
        dst,
        None,
        src.relation_inventory,
        src.status == dst.status,
        True,
        "the exact paired local outcome is recorded but is not an implemented Johnson/nonconstant-relation progress case",
    )
