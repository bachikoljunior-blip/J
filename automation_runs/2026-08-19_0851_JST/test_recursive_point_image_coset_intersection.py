from collections import deque
from math import factorial
import itertools
import random

from permutation_group_schreier import compose, identity, schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset
from recursive_point_image_coset_intersection import right_coset_intersection_recursive


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


def assert_matches_explicit(gh, gk, ar, br):
    H = schreier_stabilizer_chain(gh)
    K = schreier_stabilizer_chain(gk)
    explicit = {compose(ar, h) for h in closure(gh)} & {compose(br, k) for k in closure(gk)}
    result = right_coset_intersection_recursive(RightCoset(H, ar), RightCoset(K, br), max_nodes=200000)
    assert result.status != "undetermined_node_limit"
    if not explicit:
        assert result.status == "empty_intersection"
        return result.search_nodes
    assert result.status == "exact_intersection_coset"
    assert result.intersection_order == len(explicit)
    for p in itertools.permutations(range(len(ar))):
        assert result.coset.contains(p) == (p in explicit)
    return result.search_nodes


def test_deterministic_random_explicit_oracle_degree_1_to_6():
    rng = random.Random(1106)
    checked = 0
    for _ in range(300):
        n = rng.randint(1, 6)
        perms = list(itertools.permutations(range(n)))
        gh = [rng.choice(perms) for _ in range(rng.randint(1, 2))]
        gk = [rng.choice(perms) for _ in range(rng.randint(1, 2))]
        assert_matches_explicit(gh, gk, rng.choice(perms), rng.choice(perms))
        checked += 1
    assert checked == 300


def test_exhaustive_distinct_subgroup_cosets_degree_1_to_3():
    total = 0
    for n in range(1, 4):
        perms = list(itertools.permutations(range(n)))
        subgroups = {}
        for r in range(1, min(2, len(perms)) + 1):
            for gens in itertools.combinations(perms, r):
                subgroups.setdefault(frozenset(closure(gens)), gens)
        representatives = list(subgroups.values())
        for gh in representatives:
            for gk in representatives:
                for ar in perms:
                    for br in perms:
                        assert_matches_explicit(list(gh), list(gk), ar, br)
                        total += 1
    assert total == 1313


def sym_fix(n, fixed):
    pts = [i for i in range(n) if i != fixed]
    e = list(range(n))
    if len(pts) <= 1:
        return [tuple(e)]
    transposition = e.copy()
    transposition[pts[0]], transposition[pts[1]] = transposition[pts[1]], transposition[pts[0]]
    cycle = e.copy()
    for a, b in zip(pts, pts[1:] + pts[:1]):
        cycle[a] = b
    return [tuple(transposition), tuple(cycle)]


def test_large_point_stabilizer_intersections_do_not_enumerate_relation_orbit():
    for n in (8, 10, 12, 14):
        H = schreier_stabilizer_chain(sym_fix(n, 0))
        K = schreier_stabilizer_chain(sym_fix(n, 1))
        e = identity(n)
        result = right_coset_intersection_recursive(RightCoset(H, e), RightCoset(K, e), max_nodes=100000)
        assert H.order == factorial(n - 1)
        assert K.order == factorial(n - 1)
        assert result.status == "exact_intersection_coset"
        assert result.intersection_order == factorial(n - 2)
        assert result.search_nodes <= 8
