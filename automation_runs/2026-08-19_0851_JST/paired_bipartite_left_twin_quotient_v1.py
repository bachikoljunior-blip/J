from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable

from paired_bipartite_right_partition_provenance_v1 import _canonical_atom


@dataclass(frozen=True)
class LeftTwinQuotient:
    status: str
    original_left_size: int
    right_size: int
    class_members: tuple[tuple[int, ...], ...]
    quotient_edges: tuple[tuple[int, int], ...]
    quotient_left_colors: tuple[tuple, ...]
    right_colors: tuple[tuple, ...]
    descriptor_inventory: tuple[tuple[tuple, int], ...]
    strict_left_reduction: bool
    exact: bool
    reason: str


@dataclass(frozen=True)
class PairedLeftTwinQuotient:
    status: str
    source: LeftTwinQuotient
    target: LeftTwinQuotient
    invariant_compatible: bool
    exact_empty: bool
    quotient_reduction_complete: bool
    exact: bool
    reason: str


@dataclass(frozen=True)
class LiftedTwinQuotientIsomorphism:
    status: str
    left_map: tuple[int, ...]
    right_map: tuple[int, ...]
    exact: bool
    reason: str


def _palette(size: int, colors: Iterable[Hashable] | None, default: Hashable) -> tuple[Hashable, ...]:
    palette = tuple(default for _ in range(size)) if colors is None else tuple(colors)
    if len(palette) != size:
        raise ValueError("color sequence length mismatch")
    tuple(_canonical_atom(value) for value in palette)
    return palette


def _edge_set(left_size: int, right_size: int, edges: Iterable[tuple[int, int]]) -> set[tuple[int, int]]:
    out = set()
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("bipartite edge endpoint outside declared parts")
        out.add((a, b))
    return out


def build_left_twin_quotient(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    *,
    left_colors: Iterable[Hashable] | None = None,
    right_colors: Iterable[Hashable] | None = None,
) -> LeftTwinQuotient:
    """Collapse exact same-colored left twins into weighted quotient vertices.

    Two left vertices are equivalent iff their input colors and complete right
    neighborhoods agree exactly. The quotient left color stores both the original
    typed color and the twin-class multiplicity. Hence any color-preserving
    quotient isomorphism must match equal-size twin classes.

    Class numbering is merely a local representation; the quotient problem is an
    ordinary colored bipartite isomorphism instance and is not claimed canonical
    by its numeric class ids. The equivalence relation itself is canonical, and
    every original isomorphism descends to the quotient while every quotient
    isomorphism preserving the weighted colors lifts through arbitrary bijections
    inside matched twin classes.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 1 or n2 < 1:
        raise ValueError("left_size and right_size must be positive")
    edge_set = _edge_set(n1, n2, edges)
    lp = _palette(n1, left_colors, 0)
    rp = _palette(n2, right_colors, 1)
    encoded_left = tuple(_canonical_atom(x) for x in lp)
    encoded_right = tuple(_canonical_atom(x) for x in rp)

    neighborhoods = [[] for _ in range(n1)]
    for a, b in edge_set:
        neighborhoods[a].append(b)
    buckets: dict[tuple, list[int]] = defaultdict(list)
    for a in range(n1):
        buckets[(encoded_left[a], tuple(sorted(neighborhoods[a])))].append(a)

    # Numeric class ids are deterministic for this concrete labeled instance only.
    # Correctness does not depend on the ordering; quotient colors carry the exact
    # original color + multiplicity and the quotient graph carries adjacency.
    raw_classes = sorted((tuple(sorted(xs)) for xs in buckets.values()), key=lambda C: C[0])
    classes = tuple(raw_classes)
    class_of = {a: i for i, C in enumerate(classes) for a in C}

    quotient_edges = set()
    quotient_left_colors = []
    descriptors = []
    for i, C in enumerate(classes):
        representative = C[0]
        color = encoded_left[representative]
        quotient_color = ("left_twin_class", color, len(C))
        quotient_left_colors.append(quotient_color)
        descriptors.append((color, len(C)))
        for b in neighborhoods[representative]:
            quotient_edges.add((i, b))
        # Exact twinhood means every class member has the representative neighborhood.
        ref = tuple(sorted(neighborhoods[representative]))
        if any(tuple(sorted(neighborhoods[a])) != ref or encoded_left[a] != color for a in C):
            raise AssertionError("left twin quotient class construction is inconsistent")

    descriptor_inventory = tuple(sorted(Counter(descriptors).items()))
    strict = len(classes) < n1
    status = "left_twin_quotient_reduction" if strict else "left_twin_quotient_no_progress"
    return LeftTwinQuotient(
        status,
        n1,
        n2,
        classes,
        tuple(sorted(quotient_edges)),
        tuple(quotient_left_colors),
        encoded_right,
        descriptor_inventory,
        strict,
        True,
        (
            "exact same-colored left twin classes were collapsed; weighted quotient colors preserve original left color and multiplicity"
            if strict
            else "the full left side is already same-colored-twin-free, so quotienting does not decrease the left degree"
        ),
    )


def build_paired_left_twin_quotient(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    source_left_colors: Iterable[Hashable] | None = None,
    target_left_colors: Iterable[Hashable] | None = None,
    source_right_colors: Iterable[Hashable] | None = None,
    target_right_colors: Iterable[Hashable] | None = None,
) -> PairedLeftTwinQuotient:
    """Build the lossless paired quotient for the full-left-twin residual."""
    src = build_left_twin_quotient(
        left_size,
        right_size,
        tuple(source_edges),
        left_colors=source_left_colors,
        right_colors=source_right_colors,
    )
    dst = build_left_twin_quotient(
        left_size,
        right_size,
        tuple(target_edges),
        left_colors=target_left_colors,
        right_colors=target_right_colors,
    )
    if Counter(src.right_colors) != Counter(dst.right_colors):
        return PairedLeftTwinQuotient(
            "exact_empty_right_color_inventory",
            src,
            dst,
            False,
            True,
            True,
            True,
            "a color-preserving bipartite isomorphism must preserve the exact right input-color inventory",
        )
    if src.descriptor_inventory != dst.descriptor_inventory:
        return PairedLeftTwinQuotient(
            "exact_empty_left_twin_descriptor_inventory",
            src,
            dst,
            False,
            True,
            True,
            True,
            "any color-preserving bipartite isomorphism maps each same-colored left twin class to a twin class of the same input color and multiplicity",
        )
    if src.strict_left_reduction != dst.strict_left_reduction:
        return PairedLeftTwinQuotient(
            "exact_empty_left_twin_reduction_invariant",
            src,
            dst,
            False,
            True,
            True,
            True,
            "isomorphic instances cannot disagree on whether the canonical left twin equivalence is nontrivial",
        )
    if not src.strict_left_reduction:
        return PairedLeftTwinQuotient(
            "left_twin_quotient_no_progress",
            src,
            dst,
            True,
            False,
            False,
            True,
            "the paired left twin equivalence is discrete, so this residual reducer has no strict measure decrease",
        )
    return PairedLeftTwinQuotient(
        "paired_left_twin_quotient_reduction",
        src,
        dst,
        True,
        False,
        True,
        True,
        "every original color-preserving bipartite isomorphism descends to the weighted twin quotient and every weighted quotient isomorphism lifts through arbitrary bijections within matched equal-size twin classes",
    )


def lift_twin_quotient_isomorphism(
    source: LeftTwinQuotient,
    target: LeftTwinQuotient,
    quotient_left_map: Iterable[int],
    right_map: Iterable[int],
) -> LiftedTwinQuotientIsomorphism:
    """Validate a quotient isomorphism and lift it to the original left domain.

    The canonical sorted-to-sorted internal bijection is used only as one concrete
    lift. Because members of a twin class have identical colors and neighborhoods,
    every internal bijection between matched classes is also valid.
    """
    qmap = tuple(int(x) for x in quotient_left_map)
    rmap = tuple(int(x) for x in right_map)
    qs = len(source.class_members)
    qt = len(target.class_members)
    if qs != qt or len(qmap) != qs or sorted(qmap) != list(range(qt)):
        return LiftedTwinQuotientIsomorphism(
            "invalid_quotient_left_permutation", (), (), False,
            "quotient_left_map must be a bijection between equal-size quotient left domains",
        )
    if source.right_size != target.right_size or len(rmap) != source.right_size or sorted(rmap) != list(range(target.right_size)):
        return LiftedTwinQuotientIsomorphism(
            "invalid_right_permutation", (), (), False,
            "right_map must be a bijection between equal-size right domains",
        )

    src_q_edges = set(source.quotient_edges)
    dst_q_edges = set(target.quotient_edges)
    for i in range(qs):
        j = qmap[i]
        if source.quotient_left_colors[i] != target.quotient_left_colors[j]:
            return LiftedTwinQuotientIsomorphism(
                "quotient_left_color_mismatch", (), (), True,
                "the proposed quotient map does not preserve weighted left twin-class colors",
            )
    if any(source.right_colors[b] != target.right_colors[rmap[b]] for b in range(source.right_size)):
        return LiftedTwinQuotientIsomorphism(
            "quotient_right_color_mismatch", (), (), True,
            "the proposed right map does not preserve right input colors",
        )
    image_edges = {(qmap[i], rmap[b]) for i, b in src_q_edges}
    if image_edges != dst_q_edges:
        return LiftedTwinQuotientIsomorphism(
            "not_a_quotient_bipartite_isomorphism", (), (), True,
            "the proposed quotient/right maps do not preserve the quotient incidence relation exactly",
        )

    left_map = [-1] * source.original_left_size
    for i, source_class in enumerate(source.class_members):
        target_class = target.class_members[qmap[i]]
        if len(source_class) != len(target_class):
            raise AssertionError("weighted quotient color matched unequal twin class sizes")
        for a, c in zip(sorted(source_class), sorted(target_class)):
            left_map[a] = c
    if sorted(left_map) != list(range(target.original_left_size)):
        raise AssertionError("lifted left map is not a full permutation")
    return LiftedTwinQuotientIsomorphism(
        "lifted_twin_quotient_isomorphism",
        tuple(left_map),
        rmap,
        True,
        "the validated weighted quotient isomorphism was lifted by a concrete bijection inside each matched exact twin class",
    )
