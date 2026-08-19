from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations, product
from typing import Hashable, Iterable


@dataclass(frozen=True)
class PairedIndividualizedSubsetTWL:
    status: str
    vertex_count: int
    arity: int
    individualized_count: int
    tuple_state_count: int
    refinement_rounds: int
    stable_rank: int
    source_point_colors: tuple[int, ...]
    target_point_colors: tuple[int, ...]
    source_point_cells: tuple[tuple[int, ...], ...]
    target_point_cells: tuple[tuple[int, ...], ...]
    source_tuple_colors: tuple[int, ...]
    target_tuple_colors: tuple[int, ...]
    point_invariant_compatible: bool
    significant_point_partition: bool
    largest_point_class: int
    canonical_given_paired_individualization: bool
    exact_empty: bool
    refinement_updates_checked: int
    reason: str


def _equality_pattern(values: tuple[int, ...]) -> tuple[int, ...]:
    labels: dict[int, int] = {}
    out = []
    for value in values:
        if value not in labels:
            labels[value] = len(labels)
        out.append(labels[value])
    return tuple(out)


def _validate_individualization(
    vertex_count: int,
    arity: int,
    source: Iterable[int],
    target: Iterable[int],
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    left = tuple(int(x) for x in source)
    right = tuple(int(x) for x in target)
    if len(left) != len(right):
        raise ValueError("source and target individualization sequences must have equal length")
    if len(left) >= arity:
        raise ValueError("Design-Lemma individualization length must be at most arity-1")
    if len(set(left)) != len(left) or len(set(right)) != len(right):
        raise ValueError("individualization sequences must contain distinct vertices")
    if any(x < 0 or x >= vertex_count for x in left + right):
        raise ValueError("individualized vertex out of range")
    return left, right


def _individualization_marks(
    values: tuple[int, ...],
    individualized: tuple[int, ...],
) -> tuple[tuple[str, int] | tuple[str], ...]:
    positions = {vertex: i for i, vertex in enumerate(individualized)}
    return tuple(
        ("I", positions[value]) if value in positions else ("U",)
        for value in values
    )


def _joint_labels(source_signatures, target_signatures):
    universe = set(source_signatures).union(target_signatures)
    labels = {signature: i for i, signature in enumerate(sorted(universe, key=repr))}
    return (
        tuple(labels[signature] for signature in source_signatures),
        tuple(labels[signature] for signature in target_signatures),
    )


def _cells(colors: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    buckets: dict[int, list[int]] = {}
    for vertex, color in enumerate(colors):
        buckets.setdefault(int(color), []).append(vertex)
    return tuple(tuple(vertices) for _, vertices in sorted(buckets.items()))


def paired_individualized_complete_subset_twl(
    vertex_count: int,
    arity: int,
    source_colors: Iterable[Hashable],
    target_colors: Iterable[Hashable],
    *,
    source_individualized: Iterable[int] = (),
    target_individualized: Iterable[int] = (),
    max_tuple_states: int = 200000,
    max_rounds: int = 128,
    max_class_fraction: float = 0.9,
) -> PairedIndividualizedSubsetTWL:
    """Joint exact t-WL for complete colored t-subset relations with constants.

    The input relation has one color for every unordered t-subset.  It is lifted
    to all ordered t-tuples by recording the equality pattern, the positions of
    any paired individualized constants, and the relation color when all tuple
    entries are distinct.  Standard t-dimensional Weisfeiler--Leman refinement
    then replaces each coordinate by every ground vertex and records the exact
    coordinate-wise multisets of resulting tuple colors.

    Source and target signatures are normalized jointly in every round, so color
    identifiers are directly comparable.  The output is canonical *conditional
    on the supplied paired individualization*.  Selecting the individualization
    sequence canonically, extracting the full Design-Lemma alpha-partition/UPCC,
    and transporting it to the original Johnson domain remain separate proof
    obligations.  Tuple-state and round limits fail closed.
    """
    v = int(vertex_count)
    t = int(arity)
    if v < 2 or not 2 <= t <= v:
        raise ValueError("require 2 <= arity <= vertex_count")
    if max_tuple_states < 1 or max_rounds < 1:
        raise ValueError("tuple-state and round limits must be positive")
    if not 0.5 <= max_class_fraction < 1.0:
        raise ValueError("max_class_fraction must lie in [1/2,1)")

    source_ind, target_ind = _validate_individualization(
        v, t, source_individualized, target_individualized
    )
    coordinates = tuple(combinations(range(v), t))
    source_palette = tuple(source_colors)
    target_palette = tuple(target_colors)
    if len(source_palette) != len(coordinates) or len(target_palette) != len(coordinates):
        raise ValueError("colors must contain one entry for every unordered t-subset")

    state_count = v**t
    if state_count > max_tuple_states:
        return PairedIndividualizedSubsetTWL(
            "undetermined_twl_tuple_state_cap",
            v,
            t,
            len(source_ind),
            state_count,
            0,
            0,
            (),
            (),
            (),
            (),
            (),
            (),
            False,
            False,
            v,
            True,
            False,
            0,
            "ordered t-tuple state space exceeds the explicit n^t implementation cap",
        )

    if Counter(source_palette) != Counter(target_palette):
        return PairedIndividualizedSubsetTWL(
            "exact_empty_twl_relation_color_multiplicity",
            v,
            t,
            len(source_ind),
            state_count,
            0,
            0,
            (),
            (),
            (),
            (),
            (),
            (),
            False,
            False,
            v,
            True,
            True,
            len(source_palette) + len(target_palette),
            "complete colored t-subset relations have different color multiplicities",
        )

    subset_index = {subset: i for i, subset in enumerate(coordinates)}
    tuples = tuple(product(range(v), repeat=t))
    tuple_index = {values: i for i, values in enumerate(tuples)}

    def initial_signatures(palette, individualized):
        out = []
        for values in tuples:
            relation_color = (
                palette[subset_index[tuple(sorted(values))]]
                if len(set(values)) == t
                else ("NON_DISTINCT_TUPLE",)
            )
            out.append(
                (
                    "TUPLE",
                    _equality_pattern(values),
                    _individualization_marks(values, individualized),
                    relation_color,
                )
            )
        return tuple(out)

    source, target = _joint_labels(
        initial_signatures(source_palette, source_ind),
        initial_signatures(target_palette, target_ind),
    )
    rounds = 0
    updates_checked = 2 * state_count

    while True:
        def refined_signatures(colors):
            signatures = []
            for values in tuples:
                coordinate_multisets = []
                for position in range(t):
                    replaced = []
                    for vertex in range(v):
                        image = list(values)
                        image[position] = vertex
                        replaced.append(colors[tuple_index[tuple(image)]])
                    coordinate_multisets.append(tuple(sorted(Counter(replaced).items())))
                signatures.append(
                    (
                        "TWL",
                        colors[tuple_index[values]],
                        tuple(coordinate_multisets),
                    )
                )
            return tuple(signatures)

        source_signatures = refined_signatures(source)
        target_signatures = refined_signatures(target)
        updates_checked += 2 * state_count * t * v
        next_source, next_target = _joint_labels(source_signatures, target_signatures)
        rounds += 1
        if next_source == source and next_target == target:
            break
        source, target = next_source, next_target
        if rounds >= max_rounds:
            return PairedIndividualizedSubsetTWL(
                "undetermined_twl_round_limit",
                v,
                t,
                len(source_ind),
                state_count,
                rounds,
                0,
                (),
                (),
                (),
                (),
                (),
                (),
                False,
                False,
                v,
                True,
                False,
                updates_checked,
                "joint t-WL refinement did not stabilize within max_rounds",
            )

    source_points = tuple(source[tuple_index[(vertex,) * t]] for vertex in range(v))
    target_points = tuple(target[tuple_index[(vertex,) * t]] for vertex in range(v))
    source_cells = _cells(source_points)
    target_cells = _cells(target_points)
    compatible = Counter(source_points) == Counter(target_points)
    rank = len(set(source).union(target))

    if not compatible:
        return PairedIndividualizedSubsetTWL(
            "exact_empty_twl_point_color_inventory",
            v,
            t,
            len(source_ind),
            state_count,
            rounds,
            rank,
            source_points,
            target_points,
            source_cells,
            target_cells,
            source,
            target,
            False,
            False,
            max((len(cell) for cell in source_cells), default=v),
            True,
            True,
            updates_checked,
            "stable joint t-WL diagonal color inventories differ",
        )

    largest = max(
        max((len(cell) for cell in source_cells), default=v),
        max((len(cell) for cell in target_cells), default=v),
    )
    significant = (
        len(source_cells) > 1
        and len(target_cells) > 1
        and largest <= max_class_fraction * v + 1e-12
    )
    status = (
        "certified_paired_individualized_twl_point_partition"
        if significant
        else "stable_paired_individualized_twl_relation"
    )
    return PairedIndividualizedSubsetTWL(
        status,
        v,
        t,
        len(source_ind),
        state_count,
        rounds,
        rank,
        source_points,
        target_points,
        source_cells,
        target_cells,
        source,
        target,
        True,
        significant,
        largest,
        True,
        False,
        updates_checked,
        (
            "joint t-WL stabilized with directly comparable tuple colors; "
            + (
                "diagonal colors certify a paired alpha-bounded point partition"
                if significant
                else "no alpha-bounded point partition was certified at this paired individualization"
            )
        ),
    )
