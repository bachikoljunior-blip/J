from itertools import combinations

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from s1_string_isomorphism_v2 import s1_string_isomorphism_v2
from u3_candidate_coset_string_iso import candidate_coset_string_isomorphism_u3


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced(v, k, sigma):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}
    return tuple(index[tuple(sorted(sigma[x] for x in subset))] for subset in subsets)


def johnson_group(v, k):
    return schreier_stabilizer_chain([induced(v, k, swap01(v)), induced(v, k, cycle(v))])


def test_monochromatic_s1_terminal_is_exact_without_group_enumeration():
    H = johnson_group(9, 2)
    source = (7,) * H.degree
    got = s1_string_isomorphism_v2(H, source, source, root_n=H.degree)
    assert got.status == "exact_monochromatic_group_coset"
    assert got.exact and got.coset is not None
    assert got.coset.subgroup.order == H.order
    assert got.permutation_candidates_checked == 0


def test_large_ground_j92_star_color_closes_by_signature_split_and_orbit_recursion():
    v, k = 9, 2
    H = johnson_group(v, k)
    subsets = tuple(combinations(range(v), k))
    source = tuple(1 if 0 in subset else 0 for subset in subsets)

    sigma = cycle(v)
    q = induced(v, k, sigma)
    target = [None] * H.degree
    for i in range(H.degree):
        target[q[i]] = source[i]
    target = tuple(target)

    got = candidate_coset_string_isomorphism_u3(
        RightCoset(H, identity(H.degree)),
        source,
        target,
        root_n=H.degree,
    )
    assert got.exact, got
    assert got.coset is not None
    assert got.coset.contains(q)
    assert "johnson_ground_signature_split" in got.status

    audit = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert audit.certified, audit
