from collections import deque
from itertools import permutations
import random

from permutation_group_schreier import compose, identity, schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset
from recursive_coset_intersection import right_coset_intersection_recursive


def closure(gens):
    n = len(gens[0])
    e = identity(n)
    seen = {e}
    q = deque([e])
    while q:
        x = q.popleft()
        for g in gens:
            y = compose(x, g)
            if y not in seen:
                seen.add(y)
                q.append(y)
    return seen


def all_subgroups(n):
    ps = list(permutations(range(n)))
    uniq = {}
    for mask in range(1 << len(ps)):
        gens = [ps[i] for i in range(len(ps)) if mask & (1 << i)] or [identity(n)]
        elems = frozenset(closure(gens))
        uniq[elems] = schreier_stabilizer_chain(elems)
    return list(uniq.items())


def test_all_degree_1_to_3_subgroup_coset_pairs_match_explicit_oracle():
    checked = 0
    for n in range(1, 4):
        ps = list(permutations(range(n)))
        subs = all_subgroups(n)
        for eh, H in subs:
            for ek, K in subs:
                for a in ps:
                    for b in ps:
                        explicit = {compose(a, h) for h in eh} & {compose(b, k) for k in ek}
                        r = right_coset_intersection_recursive(RightCoset(H, a), RightCoset(K, b), max_nodes=10000)
                        if not explicit:
                            assert r.status == "empty_intersection"
                        else:
                            assert r.status == "exact_intersection_coset"
                            assert r.intersection_order == len(explicit)
                            assert all(r.coset.contains(p) == (p in explicit) for p in ps)
                        checked += 1
    assert checked == 1313


def test_500_random_degree_1_to_6_cases_match_explicit_oracle():
    rng = random.Random(110)
    for _ in range(500):
        n = rng.randint(1, 6)
        ps = list(permutations(range(n)))
        gh = [rng.choice(ps) for _ in range(rng.randint(1, 3))]
        gk = [rng.choice(ps) for _ in range(rng.randint(1, 3))]
        eh = closure(gh)
        ek = closure(gk)
        H = schreier_stabilizer_chain(gh)
        K = schreier_stabilizer_chain(gk)
        a = rng.choice(ps)
        b = rng.choice(ps)
        explicit = {compose(a, h) for h in eh} & {compose(b, k) for k in ek}
        r = right_coset_intersection_recursive(RightCoset(H, a), RightCoset(K, b), max_nodes=10000)
        assert (r.status == "exact_intersection_coset") == bool(explicit)
        if explicit:
            assert r.intersection_order == len(explicit)
            assert all(r.coset.contains(p) == (p in explicit) for p in ps)


def _point_stabilizer_symmetric_group(n, fixed):
    free = [x for x in range(n) if x != fixed]
    gens = []
    for u, v in zip(free, free[1:]):
        p = list(range(n))
        p[u], p[v] = p[v], p[u]
        gens.append(tuple(p))
    return schreier_stabilizer_chain(gens or [identity(n)])


def test_s8_two_point_stabilizers_avoid_35280_relation_images():
    H = _point_stabilizer_symmetric_group(8, 0)
    K = _point_stabilizer_symmetric_group(8, 1)
    e = identity(8)
    r = right_coset_intersection_recursive(RightCoset(H, e), RightCoset(K, e), max_nodes=100)
    assert H.order == 5040 and K.order == 5040
    assert r.status == "exact_intersection_coset" and r.intersection_order == 720
    # The equivalent complete HxK relation orbit has |H||K|/|H intersect K|
    # = 35,280 distinct images. The recursive route needs only a handful of
    # stabilizer-search nodes here.
    assert H.order * K.order // r.intersection_order == 35280
    assert r.search_nodes <= 10


def test_node_limit_fails_closed():
    H = _point_stabilizer_symmetric_group(8, 0)
    K = _point_stabilizer_symmetric_group(8, 1)
    e = identity(8)
    r = right_coset_intersection_recursive(RightCoset(H, e), RightCoset(K, e), max_nodes=1)
    assert r.status == "undetermined_node_limit"
    assert r.coset is None
