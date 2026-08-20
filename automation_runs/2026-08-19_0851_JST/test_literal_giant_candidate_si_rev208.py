from math import factorial

from coset_stabilizer_primitives import RightCoset
from literal_giant_candidate_si_v1 import exact_literal_giant_string_isomorphism, _parity
from permutation_group_schreier import identity, schreier_stabilizer_chain
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3


def _swap(n, a, b):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def _cycle3(n, a, b, c):
    p = list(range(n))
    p[a], p[b], p[c] = b, c, a
    return tuple(p)


def _symmetric_group(n):
    return schreier_stabilizer_chain(tuple(_swap(n, i, i + 1) for i in range(n - 1)))


def _alternating_group(n):
    return schreier_stabilizer_chain(tuple(_cycle3(n, 0, 1, i) for i in range(2, n)))


def test_literal_symmetric_group_returns_complete_color_stabilizer_coset():
    n = 7
    group = _symmetric_group(n)
    assert group.order == factorial(n)
    target = ("a", "a", "b", "b", "c", "c", "c")
    witness = _swap(n, 0, 2)
    source = tuple(target[witness[i]] for i in range(n))

    proof = exact_literal_giant_string_isomorphism(group, source, target, root_n=n)

    assert proof.exact
    assert proof.terminal_certified
    assert proof.coset is not None
    assert proof.coset.contains(witness)
    assert proof.coset.subgroup.order == 2 * 2 * 6


def test_literal_alternating_group_rejects_unique_odd_transporter():
    n = 7
    group = _alternating_group(n)
    assert group.order * 2 == factorial(n)
    target = tuple(range(n))
    witness = _swap(n, 0, 1)
    source = tuple(target[witness[i]] for i in range(n))

    proof = exact_literal_giant_string_isomorphism(group, source, target, root_n=n)

    assert proof.exact
    assert proof.coset is None
    assert proof.status == "exact_empty_literal_alternating_parity"


def test_literal_alternating_group_uses_color_stabilizer_to_correct_parity():
    n = 7
    group = _alternating_group(n)
    target = ("x", "x", 2, 3, 4, 5, 6)
    odd_witness = _swap(n, 0, 2)
    source = tuple(target[odd_witness[i]] for i in range(n))

    proof = exact_literal_giant_string_isomorphism(group, source, target, root_n=n)

    assert proof.exact
    assert proof.coset is not None
    assert _parity(proof.coset.representative) == 0
    assert group.contains(proof.coset.representative)
    assert all(source[i] == target[proof.coset.representative[i]] for i in range(n))
    assert proof.coset.subgroup.order == 1


def test_candidate_v3_translates_literal_alternating_solution_back_to_odd_right_coset():
    n = 7
    group = _alternating_group(n)
    representative = _swap(n, 0, 1)
    candidate = RightCoset(group, representative)
    target = tuple(range(n))
    source = tuple(target[representative[i]] for i in range(n))

    proof = candidate_coset_string_isomorphism_u3(
        candidate,
        source,
        target,
        root_n=n,
        max_group_order=8,
    )

    assert proof.exact
    assert proof.coset is not None
    assert proof.coset.contains(representative)
    assert proof.coset.subgroup.order == 1
    assert proof.status.startswith("exact_translated_")


def test_candidate_v3_delegates_nongiant_small_group_to_v2():
    n = 7
    trivial = schreier_stabilizer_chain((identity(n),))
    target = tuple(range(n))
    candidate = RightCoset(trivial, identity(n))
    proof = candidate_coset_string_isomorphism_u3(
        candidate,
        target,
        target,
        root_n=n,
        max_group_order=8,
    )
    assert proof.exact
    assert proof.coset is not None
    assert proof.coset.subgroup.order == 1
