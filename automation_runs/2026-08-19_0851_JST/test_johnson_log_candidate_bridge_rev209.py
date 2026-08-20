from itertools import combinations
from math import factorial

from candidate_full_accept_terminal_v1 import exact_if_entire_candidate_maps_string
from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import _standard_subsets
from permutation_group_schreier import identity, inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3
from u2_candidate_coset_string_iso_v4 import candidate_coset_string_isomorphism_u4


def swap(n, a, b):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def cycle(n):
    return tuple((i + 1) % n for i in range(n))


def induced_ground_group(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(index[tuple(sorted(sigma[x] for x in subset))] for subset in subsets)

    ground_gens = (swap(v, 0, 1), cycle(v))
    domain_gens = tuple(induce(g) for g in ground_gens)
    return schreier_stabilizer_chain(domain_gens), domain_gens


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def maps_string(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def stabilizes_string(values, p):
    return all(values[i] == values[p[i]] for i in range(len(values)))


def test_full_candidate_accepts_nonconstant_exact_coset_without_enumeration():
    n = 5
    # H fixes target's distinguished point 1 and freely permutes the other four.
    gens = (
        swap(n, 0, 2),
        swap(n, 2, 3),
        swap(n, 3, 4),
    )
    H = schreier_stabilizer_chain(gens)
    r = swap(n, 0, 1)
    candidate = RightCoset(H, r)
    source = (1, 0, 0, 0, 0)
    target = (0, 1, 0, 0, 0)

    got = exact_if_entire_candidate_maps_string(candidate, source, target, root_n=32)
    assert got.exact and got.coset is not None, got
    assert got.coset.subgroup.order == factorial(4)
    assert maps_string(source, target, got.coset.representative)
    for g in got.coset.subgroup.original_generators:
        assert stabilizes_string(target, g)
    check = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert check.certified, check


def test_larger_johnson_ground_uses_log_design_filter_instead_of_ground_enumeration():
    # J(9,3) lies just beyond rev173's max_explicit_degree=8 terminal.  The
    # distinguished-point string canonically induces a significant point split.
    # For the automorphism instance the exact partition-stabilizer coset is the
    # complete full-string SI fiber, so rev209 can accept it by generators rather
    # than scanning the recovered S_9 ground.  A separate test above covers a
    # non-identity source/target right-coset transporter and its action convention.
    v, k = 9, 3
    G, _domain_gens = induced_ground_group(v, k)
    subsets = _standard_subsets(v, k)
    source = tuple(int(0 in S) for S in subsets)
    target = source
    candidate = RightCoset(G, identity(G.degree))

    before = candidate_coset_string_isomorphism_u3(
        candidate,
        source,
        target,
        root_n=128,
        max_explicit_degree=8,
        max_group_order=256,
    )
    assert not before.exact, before
    assert before.status == "undetermined_johnson_ground_cap", before

    got = candidate_coset_string_isomorphism_u4(
        candidate,
        source,
        target,
        root_n=128,
        max_explicit_degree=8,
        max_group_order=256,
        max_johnson_test_sets=1000,
        max_partition_states=1024,
    )
    assert got.exact and got.coset is not None, got
    assert got.coset.subgroup.order == factorial(v - 1)
    assert G.contains(got.coset.representative)
    assert maps_string(source, target, got.coset.representative)
    for g in got.coset.subgroup.original_generators:
        assert stabilizes_string(target, g)
    check = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert check.certified, check
