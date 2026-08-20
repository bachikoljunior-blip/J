from __future__ import annotations

from itertools import combinations

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3
from u2_candidate_coset_string_iso_v4 import candidate_coset_string_isomorphism_u4


# GF(8) = GF(2)[x]/(x^3+x+1), represented as three-bit polynomials.
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


def cycle_pair_string():
    subsets = tuple(combinations(range(9), 2))
    cycle = {tuple(sorted((i, (i + 1) % 9))) for i in range(9)}
    return tuple(int(S in cycle) for S in subsets)


def outside_ground_swap_pair_action():
    # This transposition is not in PGL(2,8). Applied to the 9-cycle fixture it
    # gives another degree-2 regular graph with the same point-profile inventory,
    # but outside the PGL orbit of the source cycle. The exact solver, not this
    # comment, is the regression's certificate of emptiness.
    p = list(range(9))
    p[0], p[1] = p[1], p[0]
    return induced_pair_action(tuple(p))


def test_rev211_signed_ground_terminal_closes_profile_homogeneous_candidate_left_by_u3():
    G, gens = pgl2_8_on_pairs()
    assert G.degree == 36 and G.order == 504
    candidate = RightCoset(G, identity(36))
    source = cycle_pair_string()
    witness = gens[0]
    target = relabel_target(source, witness)

    # k=2 has no t>=2 lower-arity relation. Every ground point has the same
    # degree-2 profile, so rev209's profile partition is a single cell but does
    # not determine the nonconstant pair string. This is the intended rev211 leaf.
    old = candidate_coset_string_isomorphism_u3(
        candidate, source, target, root_n=64,
        max_group_order=128, max_explicit_degree=8,
    )
    assert not old.exact, old.status

    got = candidate_coset_string_isomorphism_u4(
        candidate, source, target, root_n=64,
        max_group_order=128,
        max_signed_ground_group_order=1024,
        max_explicit_degree=8,
    )
    assert got.exact and got.coset is not None, got.reason
    assert got.coset.contains(witness)
    assert "signed_johnson_ground_relation" in got.status
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_rev211_preserves_nontrivial_right_coset_coordinates_on_same_homogeneous_fixture():
    G, _ = pgl2_8_on_pairs()
    r = outside_ground_swap_pair_action()
    assert not G.contains(r)
    candidate = RightCoset(G, r)
    source = cycle_pair_string()
    target = relabel_target(source, r)

    got = candidate_coset_string_isomorphism_u4(
        candidate, source, target, root_n=64,
        max_group_order=128,
        max_signed_ground_group_order=1024,
        max_explicit_degree=8,
    )
    assert got.exact and got.coset is not None, got.reason
    assert got.coset.contains(r)
    assert all(source[i] == target[r[i]] for i in range(36))
    assert "signed_johnson_ground_relation" in got.status
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_rev211_signed_ground_proves_exact_empty_for_profile_homogeneous_equal_inventory_target():
    G, _ = pgl2_8_on_pairs()
    candidate = RightCoset(G, identity(36))
    source = cycle_pair_string()
    impossible = outside_ground_swap_pair_action()
    assert not G.contains(impossible)
    target = relabel_target(source, impossible)
    assert sorted(source) == sorted(target)

    old = candidate_coset_string_isomorphism_u3(
        candidate, source, target, root_n=64,
        max_group_order=128, max_explicit_degree=8,
    )
    assert not old.exact, old.status

    got = candidate_coset_string_isomorphism_u4(
        candidate, source, target, root_n=64,
        max_group_order=128,
        max_signed_ground_group_order=1024,
        max_explicit_degree=8,
    )
    assert got.exact and got.coset is None, got.status
    assert "signed_johnson_ground_relation" in got.status
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified
