from collections import deque
import numpy as np

from permutation_group_schreier import compose,identity,schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset
from product_action_coset_intersection import right_coset_intersection_product_action


def closure(gens):
    n=len(gens[0]); e=identity(n); seen={e}; q=deque([e])
    while q:
        x=q.popleft()
        for g in gens:
            y=compose(x,g)
            if y not in seen: seen.add(y); q.append(y)
    return seen


def test_random_product_action_intersections_match_explicit_coset_sets():
    rng=np.random.default_rng(108); checked=0
    for _ in range(180):
        n=int(rng.integers(1,6)); gh=[tuple(int(x) for x in rng.permutation(n)) for _ in range(int(rng.integers(1,3)))]; gk=[tuple(int(x) for x in rng.permutation(n)) for _ in range(int(rng.integers(1,3)))]; H=schreier_stabilizer_chain(gh); K=schreier_stabilizer_chain(gk); eh=closure(gh); ek=closure(gk); ar=tuple(int(x) for x in rng.permutation(n)); br=tuple(int(x) for x in rng.permutation(n)); A=RightCoset(H,ar); B=RightCoset(K,br); explicit={compose(ar,h) for h in eh}&{compose(br,k) for k in ek}; r=right_coset_intersection_product_action(A,B,max_images=10000)
        assert r.status!='undetermined_image_orbit_limit'
        if not explicit: assert r.status=='empty_intersection'
        else:
            assert r.status=='exact_intersection_coset' and r.intersection_order==len(explicit)
            assert all(r.coset.contains(g) for g in explicit)
            for _ in range(10):
                p=tuple(int(x) for x in rng.permutation(n)); assert r.coset.contains(p)==(p in explicit)
        checked+=1
    assert checked==180


def test_large_equal_s8_cosets_use_containment_shortcut_without_product_orbit():
    gens=[(1,0,2,3,4,5,6,7),(1,2,3,4,5,6,7,0)]; H=schreier_stabilizer_chain(gens); e=identity(8); A=RightCoset(H,e); B=RightCoset(H,(1,2,3,4,5,6,7,0)); r=right_coset_intersection_product_action(A,B,max_images=1)
    assert r.status=='exact_intersection_coset'
    assert r.intersection_order==40320
    assert r.product_image_orbit_size==0


def test_product_image_limit_is_fail_closed_for_noncontained_subgroups():
    # Two small generated subgroups in S6 with deliberately tiny image limit.
    H=schreier_stabilizer_chain([(1,2,0,3,4,5),(0,1,2,4,5,3)])
    K=schreier_stabilizer_chain([(1,0,2,3,4,5),(0,1,3,2,4,5)])
    A=RightCoset(H,identity(6)); B=RightCoset(K,identity(6)); r=right_coset_intersection_product_action(A,B,max_images=1)
    assert r.status in {'undetermined_image_orbit_limit','exact_intersection_coset'}
    if r.status=='undetermined_image_orbit_limit': assert r.coset is None
