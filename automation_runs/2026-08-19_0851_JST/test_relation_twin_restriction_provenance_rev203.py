from __future__ import annotations

from itertools import permutations

from relation_twin_restriction_provenance_v1 import (
    certify_paired_relation_twin_restriction,
    derive_relation_twin_restriction,
    exact_symmetric_relation_twin_classes,
)


def _edges_from_hyperedges(hyperedges):
    return {(a, b) for a, edge in enumerate(hyperedges) for b in edge}


def _relabel_hypergraph(hyperedges, left_perm, right_perm):
    mapped = [tuple(sorted(right_perm[b] for b in edge)) for edge in hyperedges]
    out = [None] * len(mapped)
    for old, new in enumerate(left_perm):
        out[new] = mapped[old]
    return out


def test_unique_large_singleton_relation_twin_class_gives_proper_restriction():
    hyperedges = [(0,), (1,), (2,)]
    got = derive_relation_twin_restriction(3, 7, _edges_from_hyperedges(hyperedges))
    assert got.status == "certified_relation_twin_restriction"
    assert got.large_twin_class == (3, 4, 5, 6)
    assert got.complement == (0, 1, 2)
    assert got.selected_part == (0, 1, 2)
    assert got.restriction.theorem_gate_verified


def test_paired_large_class_restriction_is_invariant_under_relabeling():
    hyperedges = [(0,), (1,), (2,)]
    source = _edges_from_hyperedges(hyperedges)
    right_perms = [
        tuple(range(7)),
        (6, 5, 4, 3, 2, 1, 0),
        (2, 0, 1, 4, 5, 6, 3),
    ]
    for lp in permutations(range(3)):
        for rp in right_perms:
            target = _edges_from_hyperedges(_relabel_hypergraph(hyperedges, lp, rp))
            got = certify_paired_relation_twin_restriction(3, 7, source, target)
            assert got.status == "paired_relation_twin_restriction"
            assert got.restriction_pair_complete
            assert got.selected_large_class_size == 4


def test_cycle_relation_has_no_more_than_half_twin_class():
    hyperedges = [(0, 1), (1, 2), (2, 3), (0, 3)]
    got = derive_relation_twin_restriction(4, 4, _edges_from_hyperedges(hyperedges))
    assert got.status == "relation_twin_no_large_class"
    assert got.twin_class_size_inventory == (2, 2)


def test_paired_relation_twin_inventory_mismatch_is_exact():
    cycle = [(0, 1), (1, 2), (2, 3), (0, 3)]
    triangle_tail = [(0, 1), (1, 2), (0, 2), (2, 3)]
    got = certify_paired_relation_twin_restriction(
        4,
        4,
        _edges_from_hyperedges(cycle),
        _edges_from_hyperedges(triangle_tail),
    )
    assert got.status in {
        "paired_relation_twin_status_mismatch",
        "paired_relation_twin_inventory_mismatch",
    }
    assert got.exact
    assert not got.restriction_pair_complete


def test_synthetic_symmetric_relation_twins_are_exact_transposition_classes():
    # A singleton coloring with colors [1,1,0,0,0] has classes {0,1} and {2,3,4}.
    classes = ((0, ((2,), (3,), (4,))), (1, ((0,), (1,))))
    got = exact_symmetric_relation_twin_classes(5, 1, classes)
    assert got == ((0, 1), (2, 3, 4))


def test_non_relation_outcome_fails_closed():
    complete = [(0, 1), (0, 2), (1, 2)]
    got = derive_relation_twin_restriction(3, 3, _edges_from_hyperedges(complete))
    assert got.status == "relation_twin_requires_nonconstant_containment_relation"
    assert not got.large_twin_class


def test_exhaustive_binary_pair_relations_match_direct_transposition_oracle():
    # Exhaust every binary coloring of the six unordered pairs on four points.
    # The optimized context comparison must agree with directly acting each
    # transposition on every relation coordinate.
    coords = tuple(__import__("itertools").combinations(range(4), 2))
    for mask in range(1 << len(coords)):
        buckets = {0: [], 1: []}
        color = {}
        for i, subset in enumerate(coords):
            value = 1 if mask & (1 << i) else 0
            buckets[value].append(subset)
            color[subset] = value
        classes = tuple((value, tuple(buckets[value])) for value in (0, 1) if buckets[value])
        got = exact_symmetric_relation_twin_classes(4, 2, classes)

        twin = [[False] * 4 for _ in range(4)]
        for x in range(4):
            for y in range(4):
                preserves = True
                for subset in coords:
                    image = tuple(sorted(y if z == x else x if z == y else z for z in subset))
                    if color[subset] != color[image]:
                        preserves = False
                        break
                twin[x][y] = preserves
        unseen = set(range(4))
        expected = []
        while unseen:
            x = min(unseen)
            cell = tuple(y for y in range(4) if twin[x][y])
            expected.append(cell)
            unseen -= set(cell)
        expected = tuple(sorted(expected, key=lambda cell: (len(cell), cell)))
        assert got == expected
