from math import factorial

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from primitive_giant_full_action_string_iso_v1 import (
    _parity,
    primitive_giant_full_action_string_isomorphism_terminal,
)
from s1_string_isomorphism_v2 import s1_string_isomorphism_v2
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2 as candidate_v2
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u2


def _swap(n, a, b):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def _cycle(n):
    return tuple(list(range(1, n)) + [0])


def _three_cycle(n, a, b, c):
    p = list(range(n))
    p[a], p[b], p[c] = b, c, a
    return tuple(p)


def _symmetric(n):
    G = schreier_stabilizer_chain((_swap(n, 0, 1), _cycle(n)))
    assert G.order == factorial(n)
    return G


def _alternating(n):
    G = schreier_stabilizer_chain(tuple(_three_cycle(n, 0, 1, i) for i in range(2, n)))
    assert G.order == factorial(n) // 2
    return G


def _maps(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def test_literal_s9_color_transporter_is_exact_without_group_enumeration():
    n = 9
    G = _symmetric(n)
    source = ("a", "a", "a", "a", "b", "b", "b", "b", "b")
    target = ("b", "a", "b", "a", "b", "a", "b", "a", "b")
    got = primitive_giant_full_action_string_isomorphism_terminal(G, source, target, root_n=n)
    assert got.exact and got.terminal_certified and got.coset is not None
    assert got.status == "exact_literal_symmetric_string_coset"
    assert _maps(source, target, got.coset.representative)
    assert got.coset.subgroup.order == factorial(4) * factorial(5)
    assert all(G.contains(g) for g in got.coset.subgroup.original_generators)


def test_literal_a9_color_transporter_intersects_parity_exactly():
    n = 9
    G = _alternating(n)
    source = (0, 0, 0, 1, 1, 1, 1, 1, 1)
    target = (1, 0, 1, 0, 1, 0, 1, 1, 1)
    got = primitive_giant_full_action_string_isomorphism_terminal(G, source, target, root_n=n)
    assert got.exact and got.coset is not None
    assert got.status == "exact_literal_alternating_string_coset"
    assert _parity(got.coset.representative) == 0
    assert _maps(source, target, got.coset.representative)
    assert got.coset.subgroup.order == factorial(3) * factorial(6) // 2
    assert all(G.contains(g) for g in got.coset.subgroup.original_generators)


def test_literal_a9_unique_odd_transporter_is_exact_empty():
    n = 9
    G = _alternating(n)
    source = tuple(range(n))
    target = (1, 0, 2, 3, 4, 5, 6, 7, 8)
    got = primitive_giant_full_action_string_isomorphism_terminal(G, source, target, root_n=n)
    assert got.exact and got.coset is None
    assert got.status == "exact_empty_literal_alternating_parity"


def test_candidate_v3_dispatches_large_literal_a9_before_v2_unresolved_giant_path():
    n = 9
    G = _alternating(n)
    source = (0, 0, 0, 1, 1, 1, 1, 1, 1)
    target = (1, 0, 1, 0, 1, 0, 1, 1, 1)
    candidate = RightCoset(G, identity(n))
    got = candidate_coset_string_isomorphism_u2(
        candidate,
        source,
        target,
        root_n=n,
        max_explicit_degree=8,
        max_group_order=8,
    )
    assert got.exact and got.coset is not None
    assert "exact_literal_alternating_string_coset" in got.status
    assert _maps(source, target, got.coset.representative)
    assert got.accounting.cost_certified
    assert got.accounting.terminal_certified


def test_s1_v2_dispatches_literal_s9_without_explicit_degree_or_group_enumeration():
    n = 9
    G = _symmetric(n)
    source = (0, 0, 0, 0, 1, 1, 1, 1, 1)
    target = (1, 0, 1, 0, 1, 0, 1, 0, 1)
    got = s1_string_isomorphism_v2(
        G,
        source,
        target,
        root_n=n,
        max_explicit_degree=8,
        max_group_order=8,
    )
    assert got.exact and got.coset is not None
    assert got.status == "exact_literal_symmetric_string_coset"
    assert _maps(source, target, got.coset.representative)


def test_existing_candidate_v2_intransitive_orbit_path_now_closes_s5_child_via_s1_v2():
    n = 10
    t = _swap(n, 0, 1)
    c = list(range(n))
    c[:5] = [1, 2, 3, 4, 0]
    G = schreier_stabilizer_chain((t, tuple(c)))
    assert G.order == factorial(5)
    source = (0, 0, 1, 1, 1, "x5", "x6", "x7", "x8", "x9")
    target = (1, 0, 1, 0, 1, "x5", "x6", "x7", "x8", "x9")
    got = candidate_v2(
        RightCoset(G, identity(n)),
        source,
        target,
        root_n=n,
        max_explicit_degree=4,
        max_group_order=8,
    )
    assert got.exact and got.coset is not None
    assert _maps(source, target, got.coset.representative)
    assert got.accounting.cost_certified
