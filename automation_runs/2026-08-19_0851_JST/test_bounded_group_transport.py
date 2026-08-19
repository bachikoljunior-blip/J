from collections import deque
import numpy as np

from permutation_group_schreier import compose,identity,schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset
from bounded_group_transport import act_string,bounded_right_coset_intersection,bounded_string_transporter,enumerate_group


def closure(gens):
    n=len(gens[0]); e=identity(n); seen={e}; q=deque([e])
    while q:
        x=q.popleft()
        for g in gens:
            y=compose(x,g)
            if y not in seen: seen.add(y); q.append(y)
    return seen


def test_random_bounded_string_transporters_match_exhaustive_sets():
    rng=np.random.default_rng(106)
    for _ in range(250):
        n=int(rng.integers(1,7)); gens=[tuple(int(x) for x in rng.permutation(n)) for _ in range(int(rng.integers(1,3)))]; chain=schreier_stabilizer_chain(gens); exact=closure(gens); src=tuple(int(x) for x in rng.integers(0,3,size=n)); g0=list(exact)[int(rng.integers(0,len(exact)))]; tgt=act_string(src,g0); hits={g for g in exact if act_string(src,g)==tgt}; r=bounded_string_transporter(chain,src,tgt,max_elements=1000)
        assert r.status=='exact_transporter_coset' and r.transporter_size==len(hits)
        assert all(r.coset.contains(g) for g in hits)
        for _ in range(10):
            p=tuple(int(x) for x in rng.permutation(n)); assert r.coset.contains(p)==(p in hits)


def test_random_bounded_right_coset_intersections_match_explicit_sets():
    rng=np.random.default_rng(1061)
    for _ in range(200):
        n=int(rng.integers(1,7)); ga=[tuple(int(x) for x in rng.permutation(n)) for _ in range(int(rng.integers(1,3)))]; gb=[tuple(int(x) for x in rng.permutation(n)) for _ in range(int(rng.integers(1,3)))]; ca=schreier_stabilizer_chain(ga); cb=schreier_stabilizer_chain(gb); ea=closure(ga); eb=closure(gb); ra=tuple(int(x) for x in rng.permutation(n)); rb=tuple(int(x) for x in rng.permutation(n)); A=RightCoset(ca,ra); B=RightCoset(cb,rb); explicit={compose(ra,h) for h in ea}&{compose(rb,h) for h in eb}; r=bounded_right_coset_intersection(A,B,max_elements=1000)
        if not explicit: assert r.status=='empty_intersection'
        else:
            assert r.status=='exact_intersection_coset' and r.intersection_size==len(explicit)
            assert all(r.coset.contains(g) for g in explicit)


def test_group_limit_abstains_before_enumeration():
    # S8 has order 40320, above the declared bound.
    chain=schreier_stabilizer_chain([(1,0,2,3,4,5,6,7),(1,2,3,4,5,6,7,0)])
    assert chain.order==40320
    assert enumerate_group(chain,max_elements=1000) is None
