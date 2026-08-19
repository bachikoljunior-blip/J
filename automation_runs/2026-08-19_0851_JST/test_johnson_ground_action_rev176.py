from itertools import combinations

from johnson_ground_action_v1 import recover_johnson_ground_action
from permutation_group_schreier import schreier_stabilizer_chain


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_group(v, k, *, include_complement=False):
    vertices = list(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(vertices)}
    gens = []
    for g in (swap(v), cycle(v)):
        gens.append(tuple(index[tuple(sorted(g[x] for x in subset))] for subset in vertices))
    if include_complement:
        universe = set(range(v))
        gens.append(tuple(index[tuple(sorted(universe.difference(subset)))] for subset in vertices))
    return schreier_stabilizer_chain(gens)


def test_recover_s9_action_from_j92_domain_exactly():
    H = induced_group(9, 2)
    cert = recover_johnson_ground_action(H)
    assert cert.status == "exact_johnson_ground_action"
    assert cert.ground_size == 9 and cert.subset_size == 2
    assert cert.ground_group is not None
    assert cert.original_group_order == cert.ground_group_order == 362880
    assert cert.ground_group.degree == 9


def test_recover_s7_action_from_j73_domain_exactly():
    H = induced_group(7, 3)
    cert = recover_johnson_ground_action(H)
    assert cert.status == "exact_johnson_ground_action"
    assert cert.ground_size == 7 and cert.subset_size == 3
    assert cert.ground_group is not None
    assert cert.original_group_order == cert.ground_group_order == 5040


def test_self_complementary_j63_with_complement_generator_fails_closed():
    H = induced_group(6, 3, include_complement=True)
    cert = recover_johnson_ground_action(H)
    assert cert.status == "undetermined_johnson_complement_or_nonstandard_action"
    assert cert.ground_group is None
