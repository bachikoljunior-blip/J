from __future__ import annotations

from itertools import combinations

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3
from u2_candidate_coset_string_iso_v4 import candidate_coset_string_isomorphism_u4


# GF(8) = GF(2)[x]/(x^3+x+1), encoded as three-bit polynomials.
def gf8_mul(a, b):
    out = 0
    while b:
        if b & 1:
            out ^= a
        b >>= 1
        a <<= 1
        if a & 0b1000:
            a ^= 0b1011
    return out & 0b111


def gf8_pow(a, e):
    out = 1
    while e:
        if e & 1:
            out = gf8_mul(out, a)
        a = gf8_mul(a, a)
        e >>= 1
    return out


def gf8_inv(a):
    if a == 0:
        raise ZeroDivisionError
    return gf8_pow(a, 6)


def pgl2_8_ground_generators():
    inf = 8
    translation = tuple((x ^ 1) if x != inf else inf for x in range(9))
    scale = tuple(gf8_mul(2, x) if x != inf else inf for x in range(9))
    inversion = tuple(inf if x == 0 else 0 if x == inf else gf8_inv(x) for x in range(9))
    return translation, scale, inversion


def induced_pair_action(ground_perm):
    subsets = tuple(combinations(range(9), 2))
    index = {subset: i for i, subset in enumerate(subsets)}
    return tuple(index[tuple(sorted(ground_perm[x] for x in subset))] for subset in subsets)


def pgl2_8_on_pairs():
    induced = tuple(induced_pair_action(g) for g in pgl2_8_ground_generators())
    return schreier_stabilizer_chain(induced), induced


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def _swap(n, a, b):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def test_u4_closes_large_ground_j92_pgl_candidate_that_u3_leaves_at_ground_cap():
    G, gens = pgl2_8_on_pairs()
    assert G.degree == 36 and G.order == 504
    candidate = RightCoset(G, identity(36))
    source = tuple(range(36))
    witness = gens[0]
    target = relabel_target(source, witness)

    old = candidate_coset_string_isomorphism_u3(
        candidate,
        source,
        target,
        root_n=64,
        max_group_order=128,
        max_explicit_degree=8,
    )
    assert not old.exact
    assert old.status == "undetermined_johnson_ground_cap"

    got = candidate_coset_string_isomorphism_u4(
        candidate,
        source,
        target,
        root_n=64,
        max_group_order=128,
        max_signed_ground_group_order=1024,
        max_explicit_degree=8,
    )
    assert got.exact and got.coset is not None
    assert got.coset.contains(witness)
    assert got.coset.subgroup.order == 1
    assert "signed_johnson_ground_relation" in got.status
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_u4_preserves_right_coset_translation_for_large_ground_johnson_candidate():
    G, _ = pgl2_8_on_pairs()
    r = _swap(36, 0, 1)
    assert not G.contains(r)
    candidate = RightCoset(G, r)
    source = tuple(range(36))
    target = relabel_target(source, r)

    got = candidate_coset_string_isomorphism_u4(
        candidate,
        source,
        target,
        root_n=64,
        max_group_order=128,
        max_signed_ground_group_order=1024,
        max_explicit_degree=8,
    )
    assert got.exact and got.coset is not None
    assert got.coset.contains(r)
    assert got.coset.subgroup.order == 1
    assert all(source[i] == target[r[i]] for i in range(36))
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_u4_signed_ground_can_prove_exact_empty_with_equal_color_inventory():
    G, _ = pgl2_8_on_pairs()
    candidate = RightCoset(G, identity(36))
    source = tuple(range(36))
    impossible = _swap(36, 0, 1)
    assert not G.contains(impossible)
    target = relabel_target(source, impossible)
    assert sorted(source) == sorted(target)

    got = candidate_coset_string_isomorphism_u4(
        candidate,
        source,
        target,
        root_n=64,
        max_group_order=128,
        max_signed_ground_group_order=1024,
        max_explicit_degree=8,
    )
    assert got.exact and got.coset is None
    assert "exact_empty_signed_johnson_ground_relation" in got.status
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified
