from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable


@dataclass(frozen=True)
class Provenance:
    source: str
    channel: str
    locator: str | None = None
    verified: bool = False


@dataclass(frozen=True)
class Atom:
    atom_id: str
    kind: str
    value: Any
    confidence: float
    provenance: tuple[Provenance, ...] = ()
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.atom_id or not self.kind:
            raise ValueError("atom_id and kind are required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0,1]")


@dataclass(frozen=True)
class Relation:
    relation_id: str
    subject_id: str
    predicate: str
    object_id: str
    confidence: float
    provenance: tuple[Provenance, ...] = ()

    def __post_init__(self) -> None:
        if not self.relation_id or not self.subject_id or not self.predicate or not self.object_id:
            raise ValueError("relation identity and endpoints are required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0,1]")


@dataclass
class Workspace:
    """Typed, provenance-preserving working representation."""

    atoms: dict[str, Atom] = field(default_factory=dict)
    relations: dict[str, Relation] = field(default_factory=dict)

    def add_atom(self, atom: Atom) -> None:
        if atom.atom_id in self.atoms:
            raise ValueError(f"duplicate atom_id: {atom.atom_id}")
        self.atoms[atom.atom_id] = atom

    def upsert_atom(self, atom: Atom) -> None:
        self.atoms[atom.atom_id] = atom

    def add_relation(self, relation: Relation) -> None:
        if relation.relation_id in self.relations:
            raise ValueError(f"duplicate relation_id: {relation.relation_id}")
        if relation.subject_id not in self.atoms or relation.object_id not in self.atoms:
            raise KeyError("relation endpoints must already exist in the workspace")
        self.relations[relation.relation_id] = relation

    def revise_confidence(self, atom_id: str, confidence: float, provenance: Provenance | None = None) -> Atom:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be in [0,1]")
        current = self.atoms[atom_id]
        provenance_items = current.provenance + ((provenance,) if provenance else ())
        revised = replace(current, confidence=confidence, provenance=provenance_items)
        self.atoms[atom_id] = revised
        return revised

    def neighbors(self, atom_id: str, predicate: str | None = None) -> tuple[Atom, ...]:
        ids: list[str] = []
        for rel in self.relations.values():
            if predicate is not None and rel.predicate != predicate:
                continue
            if rel.subject_id == atom_id:
                ids.append(rel.object_id)
            elif rel.object_id == atom_id:
                ids.append(rel.subject_id)
        return tuple(self.atoms[i] for i in ids)

    def select(self, *, kind: str | None = None, tags: Iterable[str] = (), min_confidence: float = 0.0) -> tuple[Atom, ...]:
        required_tags = frozenset(tags)
        return tuple(
            atom
            for atom in self.atoms.values()
            if (kind is None or atom.kind == kind)
            and atom.confidence >= min_confidence
            and required_tags.issubset(atom.tags)
        )

    def induced_subgraph(self, atom_ids: Iterable[str]) -> "Workspace":
        ids = set(atom_ids)
        missing = ids - self.atoms.keys()
        if missing:
            raise KeyError(f"unknown atoms: {sorted(missing)}")
        atoms = {i: self.atoms[i] for i in ids}
        relations = {rid: rel for rid, rel in self.relations.items() if rel.subject_id in ids and rel.object_id in ids}
        return Workspace(atoms=atoms, relations=relations)

    def merge(self, other: "Workspace") -> "Workspace":
        overlapping_atoms = set(self.atoms) & set(other.atoms)
        for atom_id in overlapping_atoms:
            if self.atoms[atom_id] != other.atoms[atom_id]:
                raise ValueError(f"conflicting atom during merge: {atom_id}")
        overlapping_relations = set(self.relations) & set(other.relations)
        for relation_id in overlapping_relations:
            if self.relations[relation_id] != other.relations[relation_id]:
                raise ValueError(f"conflicting relation during merge: {relation_id}")
        return Workspace(atoms={**self.atoms, **other.atoms}, relations={**self.relations, **other.relations})
