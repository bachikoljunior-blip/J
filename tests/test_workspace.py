from jagi.workspace import Atom, Provenance, Relation, Workspace


def test_cross_modal_atoms_can_share_one_concept():
    ws = Workspace()
    ws.add_atom(Atom("text-1", "observation:text", "red cube", 0.99, (Provenance("user", "text"),)))
    ws.add_atom(Atom("image-1", "observation:image", {"region": [1, 2, 3, 4]}, 0.80, (Provenance("camera", "image"),)))
    ws.add_atom(Atom("concept-1", "concept", "red-cube", 0.90))
    ws.add_relation(Relation("r1", "text-1", "supports", "concept-1", 0.95))
    ws.add_relation(Relation("r2", "image-1", "supports", "concept-1", 0.75))
    assert {a.atom_id for a in ws.neighbors("concept-1", "supports")} == {"text-1", "image-1"}


def test_confidence_revision_preserves_provenance():
    ws = Workspace()
    ws.add_atom(Atom("h", "hypothesis", "door is locked", 0.4, (Provenance("vision", "image"),)))
    revised = ws.revise_confidence("h", 0.8, Provenance("tool", "lock-sensor", verified=True))
    assert revised.confidence == 0.8
    assert len(revised.provenance) == 2
    assert revised.provenance[-1].verified


def test_merge_rejects_same_id_with_different_meaning():
    a = Workspace(atoms={"x": Atom("x", "concept", "cat", 0.9)})
    b = Workspace(atoms={"x": Atom("x", "concept", "dog", 0.9)})
    try:
        a.merge(b)
    except ValueError:
        pass
    else:
        raise AssertionError("conflicting identity must not merge silently")


def test_subgraph_contains_only_internal_relations():
    ws = Workspace()
    for atom_id in ("a", "b", "c"):
        ws.add_atom(Atom(atom_id, "concept", atom_id, 1.0))
    ws.add_relation(Relation("ab", "a", "links", "b", 1.0))
    ws.add_relation(Relation("bc", "b", "links", "c", 1.0))
    sub = ws.induced_subgraph(["a", "b"])
    assert set(sub.relations) == {"ab"}
