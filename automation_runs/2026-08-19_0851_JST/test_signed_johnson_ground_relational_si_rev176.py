from itertools import combinations

from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from signed_johnson_ground_relational_si_v1 import (
    signed_johnson_ground_relational_small_order_terminal,
)


# GF(8) = GF(2)[x]/(x^3+x+1), encoded by three-bit polynomials.
def gf8_mul(a, b):
    out = 0
    a = int(a)
    b = int(b)
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
    # x -> x+1, x -> alpha*x, x -> 1/x on P^1(F_8), alpha=x=2.
    translation = tuple((x ^ 1) if x != inf else inf for x in range(9))
    scale = tuple(gf8_mul(2, x) if x != inf else inf for x in range(9))
    inversion = tuple(
        inf if x == 0 else 0 if x == inf else gf8_inv(x)
        for x in range(9)
    )
    return translation, scale, inversion


def induced_pair_action(ground_perm):
    subsets = tuple(combinations(range(9), 2))
    index = {subset: i for i, subset in enumerate(subsets)}
    return tuple(
        index[tuple(sorted(ground_perm[x] for x in subset))]
        for subset in subsets
    )


def pgl2_8_on_pairs():
    ground = pgl2_8_ground_generators()
    induced = tuple(induced_pair_action(g) for g in ground)
    return schreier_stabilizer_chain(induced), induced


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def test_large_ground_j92_pgl_is_exact_without_enumerating_s9():
    G, gens = pgl2_8_on_pairs()
    assert G.degree == 36
    assert G.order == 504

    source = tuple(range(G.degree))
    witness = gens[0]
    target = relabel_target(source, witness)
    got = signed_johnson_ground_relational_small_order_terminal(
        G,
        source,
        target,
        root_n=64,
        max_group_order=1024,
    )
    assert got.status == "exact_signed_johnson_ground_relation_coset", got
    assert got.exact and got.terminal_certified and got.local_cost_certified
    assert got.ground_size == 9 and got.subset_size == 2
    assert got.domain_size == 36
    assert got.certified_signed_group_order == 504
    assert got.coset is not None and got.coset.contains(witness)
    assert got.coset.subgroup.order == 1
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_large_ground_signed_terminal_fails_closed_above_group_order_cap():
    G, _ = pgl2_8_on_pairs()
    source = tuple(i % 7 for i in range(G.degree))
    got = signed_johnson_ground_relational_small_order_terminal(
        G,
        source,
        source,
        root_n=64,
        max_group_order=128,
    )
    assert got.status == "undetermined_signed_ground_group_order_cap", got
    assert not got.exact
    assert not got.local_cost_certified
    assert got.ground_size == 9 and got.subset_size == 2
    assert got.certified_signed_group_order == 504


def test_large_ground_signed_terminal_can_certify_exact_emptiness():
    G, _ = pgl2_8_on_pairs()
    source = tuple(range(G.degree))
    target = list(source)
    target[0] = 999
    got = signed_johnson_ground_relational_small_order_terminal(
        G,
        source,
        tuple(target),
        root_n=64,
        max_group_order=1024,
    )
    assert got.status == "exact_empty_signed_johnson_ground_relation", got
    assert got.exact and got.coset is None and got.terminal_certified
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified
