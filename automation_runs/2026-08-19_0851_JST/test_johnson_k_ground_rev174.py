from itertools import combinations

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from primitive_johnson_ground_terminal_v1 import primitive_johnson_ground_string_isomorphism_terminal
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


def ground_cycle(v):
    return tuple((i + 1) % v for i in range(v))


def ground_swap(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_symmetric_action(v, k):
    vertices = list(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(vertices)}
    gens = []
    for g in (ground_swap(v), ground_cycle(v)):
        gens.append(tuple(index[tuple(sorted(g[x] for x in subset))] for subset in vertices))
    return schreier_stabilizer_chain(gens), vertices, index


def induced_perm(vertices, index, ground_perm):
    return tuple(index[tuple(sorted(ground_perm[x] for x in subset))] for subset in vertices)


def relabel_target(source, p):
    inv = [0] * len(p)
    for i, j in enumerate(p):
        inv[j] = i
    return tuple(source[inv[j]] for j in range(len(p)))


def test_j73_small_ground_terminal_is_exact():
    H, vertices, index = induced_symmetric_action(7, 3)
    assert H.degree == 35
    assert H.order == 5040
    q = induced_perm(vertices, index, ground_cycle(7))
    source = tuple(range(H.degree))
    target = relabel_target(source, q)

    got = primitive_johnson_ground_string_isomorphism_terminal(
        H,
        source,
        target,
        root_n=64,
        max_ground_degree=8,
    )
    assert got.status == "exact_primitive_johnson_ground_coset"
    assert got.exact and got.coset is not None
    assert got.coset.contains(q)
    assert got.johnson_ground_size == 7
    assert got.johnson_subset_size == 3
    assert got.ground_permutations_checked == 5040
    accounting = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert accounting.certified, accounting


def test_candidate_dispatch_closes_primitive_j73_without_s35_enumeration():
    H, vertices, index = induced_symmetric_action(7, 3)
    m = H.degree
    q = induced_perm(vertices, index, ground_cycle(7))
    source = tuple(range(m))
    target = relabel_target(source, q)
    got = candidate_coset_string_isomorphism_u2(
        RightCoset(H, identity(m)),
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=256,
    )
    assert got.status.startswith("exact_translated_exact_primitive_johnson_ground_coset")
    assert got.exact and got.coset is not None and got.coset.contains(q)
    accounting = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert accounting.certified, accounting
