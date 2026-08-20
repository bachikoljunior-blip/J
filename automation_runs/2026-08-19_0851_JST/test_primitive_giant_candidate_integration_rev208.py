from __future__ import annotations

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from s1_string_isomorphism_v2 import s1_string_isomorphism_v2
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3


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
    return schreier_stabilizer_chain(tuple(_three_cycle(n, 0, 1, i) for i in range(2, n)))


def _embed(p, start, total):
    out = list(range(total))
    for i, j in enumerate(p):
        out[start + i] = start + j
    return tuple(out)


def test_s1v2_large_s9_uses_polynomial_giant_color_terminal_not_group_enumeration():
    group = _symmetric(9)
    assert group.order == 362880
    source = (0, 0, 0, 1, 1, 2, 2, 3, 4)
    target = (0, 1, 0, 2, 0, 2, 1, 4, 3)
    got = s1_string_isomorphism_v2(
        group,
        source,
        target,
        root_n=9,
        max_group_order=256,
        max_explicit_degree=8,
    )
    assert got.exact
    assert got.status == "exact_primitive_giant_color_coset"
    assert got.operation_kind == "primitive_giant_color_terminal"
    assert got.coset is not None
    witness = got.coset.representative
    assert all(source[i] == target[witness[i]] for i in range(9))


def test_s1v2_large_a9_all_distinct_odd_unique_map_is_exact_empty():
    group = _alternating(9)
    assert group.order == 181440
    source = tuple(range(9))
    target = (1, 0, 2, 3, 4, 5, 6, 7, 8)
    got = s1_string_isomorphism_v2(
        group,
        source,
        target,
        root_n=9,
        max_group_order=256,
        max_explicit_degree=8,
    )
    assert got.exact
    assert got.status == "exact_empty_primitive_alternating_unique_odd_witness"
    assert got.coset is None


def test_u3_translates_large_a9_giant_terminal_back_to_odd_candidate_coset():
    H = _alternating(9)
    r = _transposition(9, 0, 1)
    candidate = RightCoset(H, r)
    source = tuple(range(9))
    target = r
    old = candidate_coset_string_isomorphism_u2(
        candidate,
        source,
        target,
        root_n=9,
        max_group_order=256,
        max_explicit_degree=8,
    )
    assert not old.exact
    assert old.status == "undetermined_primitive_giant_local_certificates"

    got = candidate_coset_string_isomorphism_u3(
        candidate,
        source,
        target,
        root_n=9,
        max_group_order=256,
        max_explicit_degree=8,
    )
    assert got.exact and got.coset is not None
    assert got.coset.contains(r)
    assert got.coset.subgroup.order == 1
    assert all(source[i] == target[r[i]] for i in range(9))


def test_existing_u2_intransitive_path_now_closes_large_s9_orbit_children_via_s1v2():
    s9 = _symmetric(9)
    total = 18
    gens = tuple(_embed(g, 0, total) for g in s9.original_generators) + tuple(
        _embed(g, 9, total) for g in s9.original_generators
    )
    H = schreier_stabilizer_chain(gens)
    assert H.order == 362880 * 362880
    candidate = RightCoset(H, identity(total))
    source = (0,) * 9 + (1,) * 9
    target = source
    got = candidate_coset_string_isomorphism_u2(
        candidate,
        source,
        target,
        root_n=18,
        max_group_order=256,
        max_explicit_degree=8,
    )
    assert got.exact and got.coset is not None
    assert got.status == "exact_candidate_coset_string_isomorphism_v2"
    assert got.coset.subgroup.order == H.order
    assert got.coset.contains(identity(total))
    assert len(got.children) == 2
    assert all(child.exact for child in got.children)
    assert all(child.operation_kind == "primitive_giant_color_terminal" for child in got.children)
