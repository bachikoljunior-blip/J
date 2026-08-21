from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Hashable, Iterable, Mapping


@dataclass(frozen=True)
class RelationSpec:
    """One named unary or binary relation on a finite domain."""

    name: str
    arity: int
    tuples: frozenset[tuple[Hashable, ...]]

    def __init__(
        self,
        name: str,
        arity: int,
        tuples: Iterable[Iterable[Hashable]],
    ) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("relation name must be a non-empty string")
        if arity not in (1, 2):
            raise ValueError("bounded relation-image solver supports only arity 1 or 2")

        normalized: set[tuple[Hashable, ...]] = set()
        for raw_tuple in tuples:
            try:
                relation_tuple = tuple(raw_tuple)
            except TypeError as exc:
                raise TypeError("each relation tuple must be iterable") from exc
            if len(relation_tuple) != arity:
                raise ValueError(
                    f"relation {name!r} has arity {arity}, but received tuple "
                    f"of length {len(relation_tuple)}"
                )
            for value in relation_tuple:
                try:
                    hash(value)
                except TypeError as exc:
                    raise TypeError("relation elements must be hashable") from exc
            normalized.add(relation_tuple)

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "arity", arity)
        object.__setattr__(self, "tuples", frozenset(normalized))


@dataclass(frozen=True)
class BoundedArityRelationImage:
    """A finite, named relational structure whose relation arities are at most two."""

    domain: tuple[Hashable, ...]
    relations: tuple[RelationSpec, ...]

    def __init__(
        self,
        domain: Iterable[Hashable],
        relations: Iterable[RelationSpec],
    ) -> None:
        normalized_domain = tuple(domain)
        domain_index: dict[Hashable, int] = {}
        for position, value in enumerate(normalized_domain):
            try:
                hash(value)
            except TypeError as exc:
                raise TypeError("domain elements must be hashable") from exc
            if value in domain_index:
                raise ValueError("domain elements must be unique")
            domain_index[value] = position

        normalized_relations = tuple(relations)
        seen_names: set[str] = set()
        for relation in normalized_relations:
            if not isinstance(relation, RelationSpec):
                raise TypeError("relations must be RelationSpec instances")
            if relation.name in seen_names:
                raise ValueError(f"duplicate relation name: {relation.name!r}")
            seen_names.add(relation.name)
            for relation_tuple in relation.tuples:
                for value in relation_tuple:
                    if value not in domain_index:
                        raise ValueError(
                            f"relation {relation.name!r} contains an element outside the domain"
                        )

        object.__setattr__(self, "domain", normalized_domain)
        object.__setattr__(self, "relations", normalized_relations)

    def relation(self, name: str) -> RelationSpec:
        for relation in self.relations:
            if relation.name == name:
                return relation
        raise KeyError(name)


@dataclass(frozen=True)
class BoundedArityRelationImageWitness:
    """A checked source-to-target bijection returned by the exact solver."""

    source_domain: tuple[Hashable, ...]
    target_domain: tuple[Hashable, ...]
    image_indices: tuple[int, ...]
    refinement_rounds: int
    candidates_checked: int

    @property
    def exact(self) -> bool:
        return True

    @property
    def mapping(self) -> dict[Hashable, Hashable]:
        return {
            source: self.target_domain[target_index]
            for source, target_index in zip(self.source_domain, self.image_indices)
        }

    def image_of(self, source: Hashable) -> Hashable:
        try:
            source_index = self.source_domain.index(source)
        except ValueError as exc:
            raise KeyError(source) from exc
        return self.target_domain[self.image_indices[source_index]]


@dataclass(frozen=True)
class _IndexedRelationImage:
    domain: tuple[Hashable, ...]
    unary: dict[str, frozenset[int]]
    binary: dict[str, frozenset[tuple[int, int]]]
    outgoing: dict[str, tuple[frozenset[int], ...]]
    incoming: dict[str, tuple[frozenset[int], ...]]


def _index_relation_image(image: BoundedArityRelationImage) -> _IndexedRelationImage:
    index = {value: position for position, value in enumerate(image.domain)}
    unary: dict[str, frozenset[int]] = {}
    binary: dict[str, frozenset[tuple[int, int]]] = {}
    outgoing: dict[str, tuple[frozenset[int], ...]] = {}
    incoming: dict[str, tuple[frozenset[int], ...]] = {}
    n = len(image.domain)

    for relation in image.relations:
        if relation.arity == 1:
            unary[relation.name] = frozenset(index[entry[0]] for entry in relation.tuples)
            continue

        edges = frozenset((index[left], index[right]) for left, right in relation.tuples)
        binary[relation.name] = edges
        out_sets = [set() for _ in range(n)]
        in_sets = [set() for _ in range(n)]
        for left, right in edges:
            out_sets[left].add(right)
            in_sets[right].add(left)
        outgoing[relation.name] = tuple(frozenset(values) for values in out_sets)
        incoming[relation.name] = tuple(frozenset(values) for values in in_sets)

    return _IndexedRelationImage(
        domain=image.domain,
        unary=unary,
        binary=binary,
        outgoing=outgoing,
        incoming=incoming,
    )


def _relation_signature(image: BoundedArityRelationImage) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        sorted((relation.name, relation.arity, len(relation.tuples)) for relation in image.relations)
    )


def _joint_colors(
    source_signatures: tuple[tuple, ...],
    target_signatures: tuple[tuple, ...],
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    palette = {
        signature: color
        for color, signature in enumerate(sorted(set(source_signatures + target_signatures)))
    }
    return (
        tuple(palette[signature] for signature in source_signatures),
        tuple(palette[signature] for signature in target_signatures),
    )


def _initial_colors(
    source: _IndexedRelationImage,
    target: _IndexedRelationImage,
    unary_names: tuple[str, ...],
    binary_names: tuple[str, ...],
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    def signatures(image: _IndexedRelationImage) -> tuple[tuple, ...]:
        result: list[tuple] = []
        for vertex in range(len(image.domain)):
            unary_signature = tuple(
                int(vertex in image.unary[name]) for name in unary_names
            )
            binary_signature = tuple(
                (
                    int((vertex, vertex) in image.binary[name]),
                    len(image.outgoing[name][vertex]),
                    len(image.incoming[name][vertex]),
                )
                for name in binary_names
            )
            result.append((unary_signature, binary_signature))
        return tuple(result)

    return _joint_colors(signatures(source), signatures(target))


def _refine_colors(
    source: _IndexedRelationImage,
    target: _IndexedRelationImage,
    source_colors: tuple[int, ...],
    target_colors: tuple[int, ...],
    binary_names: tuple[str, ...],
) -> tuple[tuple[int, ...], tuple[int, ...], int] | None:
    rounds = 0

    def signatures(
        image: _IndexedRelationImage,
        colors: tuple[int, ...],
    ) -> tuple[tuple, ...]:
        result: list[tuple] = []
        for vertex in range(len(image.domain)):
            relation_profiles: list[tuple] = []
            for name in binary_names:
                outgoing_colors = tuple(
                    sorted(Counter(colors[neighbor] for neighbor in image.outgoing[name][vertex]).items())
                )
                incoming_colors = tuple(
                    sorted(Counter(colors[neighbor] for neighbor in image.incoming[name][vertex]).items())
                )
                relation_profiles.append((outgoing_colors, incoming_colors))
            result.append((colors[vertex], tuple(relation_profiles)))
        return tuple(result)

    if Counter(source_colors) != Counter(target_colors):
        return None

    while True:
        new_source, new_target = _joint_colors(
            signatures(source, source_colors),
            signatures(target, target_colors),
        )
        rounds += 1
        if Counter(new_source) != Counter(new_target):
            return None
        if new_source == source_colors and new_target == target_colors:
            return new_source, new_target, rounds
        source_colors, target_colors = new_source, new_target


def verify_bounded_arity_relation_image_isomorphism(
    source: BoundedArityRelationImage,
    target: BoundedArityRelationImage,
    mapping: Mapping[Hashable, Hashable],
) -> bool:
    """Return whether ``mapping`` is a bijection preserving every named relation."""

    if len(source.domain) != len(target.domain):
        return False
    if _relation_signature(source) != _relation_signature(target):
        return False
    if set(mapping.keys()) != set(source.domain):
        return False

    image_values = tuple(mapping[value] for value in source.domain)
    if len(set(image_values)) != len(target.domain) or set(image_values) != set(target.domain):
        return False

    target_relations = {relation.name: relation for relation in target.relations}
    for relation in source.relations:
        transported = frozenset(
            tuple(mapping[value] for value in relation_tuple)
            for relation_tuple in relation.tuples
        )
        if transported != target_relations[relation.name].tuples:
            return False
    return True


def find_bounded_arity_relation_image_isomorphism(
    source: BoundedArityRelationImage,
    target: BoundedArityRelationImage,
) -> BoundedArityRelationImageWitness | None:
    """Find an exact isomorphism witness for finite named unary/binary structures.

    Joint color refinement is used only as an isomorphism-invariant pruning step.
    Acceptance is always backed by a complete relation check.  When refinement
    does not decide the instance, deterministic color-respecting backtracking is
    exhaustive; therefore ``None`` is an exact non-isomorphism result rather than
    a heuristic rejection.  The search can still be exponential on highly
    symmetric inputs.
    """

    if not isinstance(source, BoundedArityRelationImage) or not isinstance(
        target, BoundedArityRelationImage
    ):
        raise TypeError("source and target must be BoundedArityRelationImage instances")
    if len(source.domain) != len(target.domain):
        return None
    if _relation_signature(source) != _relation_signature(target):
        return None

    source_indexed = _index_relation_image(source)
    target_indexed = _index_relation_image(target)
    unary_names = tuple(sorted(source_indexed.unary))
    binary_names = tuple(sorted(source_indexed.binary))
    source_colors, target_colors = _initial_colors(
        source_indexed,
        target_indexed,
        unary_names,
        binary_names,
    )
    refined = _refine_colors(
        source_indexed,
        target_indexed,
        source_colors,
        target_colors,
        binary_names,
    )
    if refined is None:
        return None
    source_colors, target_colors, refinement_rounds = refined

    n = len(source.domain)
    if n == 0:
        return BoundedArityRelationImageWitness(
            source_domain=source.domain,
            target_domain=target.domain,
            image_indices=(),
            refinement_rounds=refinement_rounds,
            candidates_checked=0,
        )

    target_by_color: dict[int, tuple[int, ...]] = {}
    for color in sorted(set(target_colors)):
        target_by_color[color] = tuple(
            vertex for vertex, vertex_color in enumerate(target_colors) if vertex_color == color
        )

    source_to_target = [-1] * n
    target_used = [False] * n
    candidates_checked = 0

    def unmapped_neighbor_profile(
        image: _IndexedRelationImage,
        vertex: int,
        colors: tuple[int, ...],
        unavailable: list[bool],
        relation_name: str,
    ) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
        outgoing_profile = tuple(
            sorted(
                Counter(
                    colors[neighbor]
                    for neighbor in image.outgoing[relation_name][vertex]
                    if not unavailable[neighbor]
                ).items()
            )
        )
        incoming_profile = tuple(
            sorted(
                Counter(
                    colors[neighbor]
                    for neighbor in image.incoming[relation_name][vertex]
                    if not unavailable[neighbor]
                ).items()
            )
        )
        return outgoing_profile, incoming_profile

    def compatible(source_vertex: int, target_vertex: int) -> bool:
        if source_colors[source_vertex] != target_colors[target_vertex]:
            return False

        for name in unary_names:
            if (source_vertex in source_indexed.unary[name]) != (
                target_vertex in target_indexed.unary[name]
            ):
                return False

        source_unavailable = [mapped_target >= 0 for mapped_target in source_to_target]
        for name in binary_names:
            source_edges = source_indexed.binary[name]
            target_edges = target_indexed.binary[name]
            if ((source_vertex, source_vertex) in source_edges) != (
                (target_vertex, target_vertex) in target_edges
            ):
                return False

            for other_source, other_target in enumerate(source_to_target):
                if other_target < 0:
                    continue
                if ((source_vertex, other_source) in source_edges) != (
                    (target_vertex, other_target) in target_edges
                ):
                    return False
                if ((other_source, source_vertex) in source_edges) != (
                    (other_target, target_vertex) in target_edges
                ):
                    return False

            if unmapped_neighbor_profile(
                source_indexed,
                source_vertex,
                source_colors,
                source_unavailable,
                name,
            ) != unmapped_neighbor_profile(
                target_indexed,
                target_vertex,
                target_colors,
                target_used,
                name,
            ):
                return False

        return True

    def choose_source_vertex() -> int:
        unmapped = [vertex for vertex, target_vertex in enumerate(source_to_target) if target_vertex < 0]
        return min(
            unmapped,
            key=lambda vertex: (
                sum(not target_used[candidate] for candidate in target_by_color[source_colors[vertex]]),
                vertex,
            ),
        )

    def search() -> tuple[int, ...] | None:
        nonlocal candidates_checked
        if all(target_vertex >= 0 for target_vertex in source_to_target):
            mapping = {
                source.domain[source_vertex]: target.domain[target_vertex]
                for source_vertex, target_vertex in enumerate(source_to_target)
            }
            if verify_bounded_arity_relation_image_isomorphism(source, target, mapping):
                return tuple(source_to_target)
            return None

        source_vertex = choose_source_vertex()
        for target_vertex in target_by_color[source_colors[source_vertex]]:
            if target_used[target_vertex]:
                continue
            candidates_checked += 1
            if not compatible(source_vertex, target_vertex):
                continue
            source_to_target[source_vertex] = target_vertex
            target_used[target_vertex] = True
            witness = search()
            if witness is not None:
                return witness
            target_used[target_vertex] = False
            source_to_target[source_vertex] = -1
        return None

    image_indices = search()
    if image_indices is None:
        return None
    witness = BoundedArityRelationImageWitness(
        source_domain=source.domain,
        target_domain=target.domain,
        image_indices=image_indices,
        refinement_rounds=refinement_rounds,
        candidates_checked=candidates_checked,
    )
    if not verify_bounded_arity_relation_image_isomorphism(source, target, witness.mapping):
        raise AssertionError("internal relation-image witness verification failed")
    return witness


__all__ = [
    "BoundedArityRelationImage",
    "BoundedArityRelationImageWitness",
    "RelationSpec",
    "find_bounded_arity_relation_image_isomorphism",
    "verify_bounded_arity_relation_image_isomorphism",
]
