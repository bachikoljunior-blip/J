from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import ceil, comb, log2
from typing import Hashable, Iterable

from paired_bipartite_right_partition_provenance_v1 import (
    CanonicalAtom,
    SignatureInventory,
    _canonical_atom,
    _normalize_edges,
    _palette,
    derive_canonical_right_partition,
)

HigherArityRelationSignature = tuple[
    tuple[tuple[CanonicalAtom, int], ...],
    tuple[tuple[CanonicalAtom, tuple[int, ...]], ...],
]
HigherArityRelationInventory = tuple[tuple[HigherArityRelationSignature, int], ...]


@dataclass(frozen=True)
class CanonicalHigherArityRightRelation:
    status: str
    left_color_inventory: tuple[tuple[CanonicalAtom, int], ...]
    first_order_signature_inventory: SignatureInventory
    selected_arity: int | None
    arity_cap: int
    tested_arities: tuple[int, ...]
    tested_subset_count: int
    arity_relation_inventories: tuple[tuple[int, HigherArityRelationInventory], ...]
    relation_inventory: HigherArityRelationInventory
    subset_signatures: tuple[tuple[tuple[int, ...], HigherArityRelationSignature], ...]
    relation_nonconstant: bool
    exact: bool
    reason: str


@dataclass(frozen=True)
class PairedHigherArityRightRelationProvenance:
    status: str
    source_relation: CanonicalHigherArityRightRelation
    target_relation: CanonicalHigherArityRightRelation
    selected_arity: int | None
    provenance_verified: bool
    exact: bool
    reason: str


def _left_color_inventory(colors: tuple[Hashable, ...]) -> tuple[tuple[CanonicalAtom, int], ...]:
    counts = Counter(_canonical_atom(value) for value in colors)
    return tuple(sorted(counts.items()))


def _relation_for_arity(
    left_size: int,
    right_size: int,
    edge_set: set[tuple[int, int]],
    left_colors: tuple[Hashable, ...],
    right_colors: tuple[Hashable, ...],
    arity: int,
) -> tuple[
    HigherArityRelationInventory,
    tuple[tuple[tuple[int, ...], HigherArityRelationSignature], ...],
]:
    """Exact label-invariant t-subset relation induced by bipartite incidence.

    A t-subset S of the right part is colored by:
      * the multiset of right input colors on S; and
      * for each left input color, the histogram of left vertices having exactly
        j neighbors in S, for j=0..t.

    Internal ordering of S never enters the color. Every color-preserving
    bipartite isomorphism therefore maps each t-subset to a t-subset of exactly
    the same relation color.
    """
    t = int(arity)
    if not 2 <= t <= right_size:
        raise ValueError("arity must lie in [2,right_size]")

    encoded_left = tuple(_canonical_atom(value) for value in left_colors)
    encoded_right = tuple(_canonical_atom(value) for value in right_colors)

    left_buckets: dict[CanonicalAtom, list[int]] = defaultdict(list)
    for a, color in enumerate(encoded_left):
        left_buckets[color].append(a)
    ordered_left_colors = tuple(sorted(left_buckets))

    neighbors = [set() for _ in range(left_size)]
    for a, b in edge_set:
        neighbors[a].add(b)

    colored_subsets = []
    for subset in combinations(range(right_size), t):
        subset_set = set(subset)
        right_multiset = tuple(sorted(Counter(encoded_right[b] for b in subset).items()))
        occupancy = []
        for color in ordered_left_colors:
            histogram = [0] * (t + 1)
            for a in left_buckets[color]:
                histogram[len(neighbors[a].intersection(subset_set))] += 1
            occupancy.append((color, tuple(histogram)))
        signature: HigherArityRelationSignature = (right_multiset, tuple(occupancy))
        colored_subsets.append((tuple(subset), signature))

    inventory = tuple(sorted(Counter(sig for _, sig in colored_subsets).items()))
    return inventory, tuple(colored_subsets)


def derive_canonical_higher_arity_right_relation(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    *,
    left_colors: Iterable[Hashable] | None = None,
    right_colors: Iterable[Hashable] | None = None,
    max_arity: int | None = None,
    max_relation_subsets: int = 200000,
) -> CanonicalHigherArityRightRelation:
    """Derive the first informative canonical right t-subset relation.

    This layer is entered only after rev201's degree/color right partition is
    homogeneous. It examines t=2,3,... canonically and selects the first arity
    whose exact relation has more than one color. The default cap is
    ceil(log2(|V2|)), matching the logarithmic-arity discipline used elsewhere
    in the AGI-GI rev series. Enumeration is fail-closed under an explicit
    per-arity subset cap.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 1 or n2 < 2:
        raise ValueError("higher-arity right relation requires left_size>=1 and right_size>=2")
    if max_relation_subsets < 1:
        raise ValueError("max_relation_subsets must be positive")

    edge_tuple = tuple(edges)
    edge_set = _normalize_edges(n1, n2, edge_tuple)
    left_palette = _palette(n1, left_colors, 0)
    right_palette = _palette(n2, right_colors, 1)
    first = derive_canonical_right_partition(
        n1,
        n2,
        edge_tuple,
        left_colors=left_palette,
        right_colors=right_palette,
    )
    left_inventory = _left_color_inventory(left_palette)

    if max_arity is None:
        arity_cap = min(n2, max(2, ceil(log2(max(2, n2)))))
    else:
        arity_cap = min(n2, int(max_arity))
        if arity_cap < 2:
            raise ValueError("max_arity must be at least 2")

    if first.status == "canonical_right_partition":
        return CanonicalHigherArityRightRelation(
            "first_order_right_partition_available",
            left_inventory,
            first.right_signature_inventory,
            None,
            arity_cap,
            (),
            0,
            (),
            (),
            (),
            False,
            True,
            "rev201 already exposes a proper canonical right partition; higher-arity provenance is not the active residual",
        )

    tested_arities = []
    tested_subset_count = 0
    arity_inventories = []
    for t in range(2, arity_cap + 1):
        subset_count = comb(n2, t)
        if subset_count > max_relation_subsets:
            return CanonicalHigherArityRightRelation(
                "higher_arity_relation_test_cap_exceeded",
                left_inventory,
                first.right_signature_inventory,
                None,
                arity_cap,
                tuple(tested_arities),
                tested_subset_count,
                tuple(arity_inventories),
                (),
                (),
                False,
                True,
                "the next canonical right-relation arity exceeds the explicit subset-enumeration cap; no progress is claimed",
            )
        inventory, subset_signatures = _relation_for_arity(
            n1,
            n2,
            edge_set,
            left_palette,
            right_palette,
            t,
        )
        tested_arities.append(t)
        tested_subset_count += subset_count
        arity_inventories.append((t, inventory))
        if len(inventory) > 1:
            return CanonicalHigherArityRightRelation(
                "canonical_higher_arity_right_relation",
                left_inventory,
                first.right_signature_inventory,
                t,
                arity_cap,
                tuple(tested_arities),
                tested_subset_count,
                tuple(arity_inventories),
                inventory,
                subset_signatures,
                True,
                True,
                "the first informative right t-subset incidence relation is nonconstant and uses only color/incidence invariants preserved by every color-preserving bipartite isomorphism",
            )

    return CanonicalHigherArityRightRelation(
        "higher_arity_right_relation_no_progress",
        left_inventory,
        first.right_signature_inventory,
        None,
        arity_cap,
        tuple(tested_arities),
        tested_subset_count,
        tuple(arity_inventories),
        (),
        (),
        False,
        True,
        "all tested canonical right t-subset incidence relations are homogeneous; a stronger coherent/Design provenance layer is required",
    )


def certify_paired_higher_arity_right_relation_provenance(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    source_left_colors: Iterable[Hashable] | None = None,
    target_left_colors: Iterable[Hashable] | None = None,
    source_right_colors: Iterable[Hashable] | None = None,
    target_right_colors: Iterable[Hashable] | None = None,
    max_arity: int | None = None,
    max_relation_subsets: int = 200000,
) -> PairedHigherArityRightRelationProvenance:
    """Pair the homogeneous degree/color residual through a canonical relation.

    Exact relation-color multiplicities are compared at every tested arity.
    The first nonconstant relation is accepted only when source and target have
    the identical canonical inventory. This proves provenance of the relation,
    not an ambient transporter, coherent closure, full-string isomorphism set,
    or recursive Split-or-Johnson conclusion.
    """
    src = derive_canonical_higher_arity_right_relation(
        left_size,
        right_size,
        tuple(source_edges),
        left_colors=source_left_colors,
        right_colors=source_right_colors,
        max_arity=max_arity,
        max_relation_subsets=max_relation_subsets,
    )
    dst = derive_canonical_higher_arity_right_relation(
        left_size,
        right_size,
        tuple(target_edges),
        left_colors=target_left_colors,
        right_colors=target_right_colors,
        max_arity=max_arity,
        max_relation_subsets=max_relation_subsets,
    )

    if src.left_color_inventory != dst.left_color_inventory:
        return PairedHigherArityRightRelationProvenance(
            "left_color_inventory_mismatch",
            src,
            dst,
            None,
            False,
            True,
            "a color-preserving bipartite isomorphism must preserve the exact left input-color inventory",
        )
    if src.first_order_signature_inventory != dst.first_order_signature_inventory:
        return PairedHigherArityRightRelationProvenance(
            "first_order_right_signature_inventory_mismatch",
            src,
            dst,
            None,
            False,
            True,
            "the exact rev201 right degree/color-signature inventories differ",
        )

    src_by_arity = dict(src.arity_relation_inventories)
    dst_by_arity = dict(dst.arity_relation_inventories)
    for t in sorted(set(src_by_arity).intersection(dst_by_arity)):
        if src_by_arity[t] != dst_by_arity[t]:
            return PairedHigherArityRightRelationProvenance(
                "higher_arity_relation_inventory_mismatch",
                src,
                dst,
                t,
                False,
                True,
                "a color-preserving bipartite isomorphism must preserve every canonical right t-subset relation color and its multiplicity",
            )

    if src.status == "first_order_right_partition_available" or dst.status == "first_order_right_partition_available":
        if src.status != dst.status:
            return PairedHigherArityRightRelationProvenance(
                "first_order_progress_status_mismatch",
                src,
                dst,
                None,
                False,
                True,
                "equal first-order inventories unexpectedly yielded different deterministic progress statuses",
            )
        return PairedHigherArityRightRelationProvenance(
            "first_order_right_partition_available",
            src,
            dst,
            None,
            True,
            True,
            "rev201 already supplies the canonical provenance; the higher-arity residual is not entered",
        )

    if (
        src.status == "canonical_higher_arity_right_relation"
        and dst.status == "canonical_higher_arity_right_relation"
        and src.selected_arity == dst.selected_arity
        and src.relation_inventory == dst.relation_inventory
    ):
        return PairedHigherArityRightRelationProvenance(
            "paired_higher_arity_right_relation_provenance",
            src,
            dst,
            src.selected_arity,
            True,
            True,
            "every color-preserving bipartite isomorphism maps the selected source right t-subset relation to the target relation with identical exact color inventory; coherent closure and ambient transport remain separate obligations",
        )

    if src.status == dst.status == "higher_arity_right_relation_no_progress":
        return PairedHigherArityRightRelationProvenance(
            "higher_arity_right_relation_no_progress",
            src,
            dst,
            None,
            True,
            True,
            "the paired exact inventories agree but all tested logarithmic-arity right relations remain homogeneous",
        )

    if src.status == dst.status == "higher_arity_relation_test_cap_exceeded":
        return PairedHigherArityRightRelationProvenance(
            "higher_arity_relation_test_cap_exceeded",
            src,
            dst,
            None,
            True,
            True,
            "the paired residual reaches the explicit enumeration cap before an informative canonical relation is certified",
        )

    return PairedHigherArityRightRelationProvenance(
        "paired_higher_arity_relation_status_mismatch",
        src,
        dst,
        None,
        False,
        True,
        "source and target reached different canonical higher-arity statuses; no paired provenance is claimed",
    )
