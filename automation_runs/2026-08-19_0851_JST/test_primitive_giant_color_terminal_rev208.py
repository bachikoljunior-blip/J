from __future__ import annotations

from certified_group_enumeration_v1 import enumerate_schreier_group_exact
from permutation_group_schreier import identity, schreier_stabilizer_chain
from primitive_giant_color_terminal_v1 import (
    permutation_parity,
    primitive_giant_color_string_isomorphism_terminal,
)


def _transposition(n, a, b):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def _cycle(n):
    return tuple((i + 1) % n for i in range(n))


def _three_cycle(n, a, b, c):
    p = list(range(n))
    p[a], p[b], p[c] = b, c, a
    return tuple(p)


def _symmetric(n):
    return schreier_stabilizer_chain((_transposition(n, 0, 1), _cycle(n)))


def _alternating(n):
    # The 3-cycles (0 1 i) generate A_n.
    return schreier_stabilizer_chain(tuple(_three_cycle(n, 0, 1, i) for i in range(2, n)))


def _exact_matches(group, source, target):
    elements = enumerate_schreier_group_exact(group, max_elements=1000)
    assert elements is not None and len(elements) == group.order
    return tuple(g for g in elements if all(source[i] == target[g[i]] for i in range(group.degree)))


def _audit(group, source, target, result):
    matches = _exact_matches(group, source, target)
    if not matches:
        assert result.coset is None
        return
    assert result.coset is not None
    reconstructed = tuple(g for g in enumerate_schreier_group_exact(group, max_elements=1000) if result.coset.contains(g))
    assert reconstructed == matches
    assert result.coset.subgroup.order == len(matches)


def test_s5_repeated_colors_reconstruct_full_exact_solution_coset():
    group = _symmetric(5)
    assert group.order == 120
    source = ("a", "a", "b", "b", "b")
    target = ("b", "a", "b", "a", "b")
    got = primitive_giant_color_string_isomorphism_terminal(group, source, target, root_n=5)
    assert got.status == "exact_primitive_giant_color_coset"
    assert got.giant_type == "S_n"
    assert got.exact_stabilizer_order == 2 * 6
    _audit(group, source, target, got)


def test_a5_repeated_color_toggles_odd_canonical_witness_and_stays_exact():
    group = _alternating(5)
    assert group.order == 60
    source = (0, 0, 1, 2, 3)
    # The occurrence-order color witness swaps positions 0 and 1 and is odd;
    # the repeated zero class supplies a target-color parity toggle.
    target = (0, 0, 1, 2, 3)
    # Identity itself is even, so force a target order whose canonical witness is odd.
    target = (0, 1, 0, 2, 3)
    got = primitive_giant_color_string_isomorphism_terminal(group, source, target, root_n=5)
    assert got.status == "exact_primitive_giant_color_coset"
    assert got.giant_type == "A_n"
    assert got.witness_parity == 0
    assert all(permutation_parity(g) == 0 for g in got.coset.subgroup.original_generators)
    _audit(group, source, target, got)


def test_a5_all_distinct_unique_odd_color_map_is_exact_empty():
    group = _alternating(5)
    source = (0, 1, 2, 3, 4)
    target = (1, 0, 2, 3, 4)
    got = primitive_giant_color_string_isomorphism_terminal(group, source, target, root_n=5)
    assert got.status == "exact_empty_primitive_alternating_unique_odd_witness"
    assert got.coset is None
    _audit(group, source, target, got)


def test_a5_all_distinct_unique_even_color_map_is_singleton_coset():
    group = _alternating(5)
    source = (0, 1, 2, 3, 4)
    target = (1, 2, 0, 3, 4)
    got = primitive_giant_color_string_isomorphism_terminal(group, source, target, root_n=5)
    assert got.status == "exact_primitive_giant_color_coset"
    assert got.exact_stabilizer_order == 1
    assert got.witness_parity == 0
    _audit(group, source, target, got)


def test_giant_color_inventory_mismatch_is_exact_empty_without_enumerating_group():
    group = _symmetric(5)
    source = (0, 0, 1, 1, 2)
    target = (0, 0, 1, 2, 2)
    got = primitive_giant_color_string_isomorphism_terminal(group, source, target, root_n=5)
    assert got.status == "exact_empty_primitive_giant_color_multiplicity"
    assert got.coset is None
    _audit(group, source, target, got)


def test_terminal_rejects_non_giant_group():
    group = schreier_stabilizer_chain((identity(5),))
    try:
        primitive_giant_color_string_isomorphism_terminal(group, (0,) * 5, (0,) * 5, root_n=5)
    except ValueError as exc:
        assert "exactly A_n or S_n" in str(exc)
    else:
        raise AssertionError("non-giant group was incorrectly accepted")
