from collections import deque
import numpy as np

from permutation_group_schreier import compose,identity
from bounded_group_transport import act_string
from state_orbit_schreier import string_orbit_stabilizer_transporter


def closure(gens):
    n=len(gens[0]); e=identity(n); seen={e}; q=deque([e])
    while q:
        x=q.popleft()
        for g in gens:
            y=compose(x,g)
            if y not in seen: seen.add(y); q.append(y)
    return seen


def test_random_state_orbit_stabilizer_and_transporters_match_full_group_enumeration():
    rng=np.random.default_rng(107)
    for _ in range(250):
        n=int(rng.integers(1,7)); gens=[tuple(int(x) for x in rng.permutation(n)) for _ in range(int(rng.integers(1,3)))]; exact=closure(gens); src=tuple(int(x) for x in rng.integers(0,3,size=n)); g0=list(exact)[int(rng.integers(0,len(exact)))]; tgt=act_string(src,g0)
        stabilizer={g for g in exact if act_string(src,g)==src}; hits={g for g in exact if act_string(src,g)==tgt}; orbit={act_string(src,g) for g in exact}
        r=string_orbit_stabilizer_transporter(gens,src,tgt,max_images=1000)
        assert r.status=='exact_transporter_coset' and r.orbit_size==len(orbit)
        assert r.stabilizer.order==len(stabilizer) and all(r.stabilizer.contains(g) for g in stabilizer)
        assert r.transporter.subgroup.order==len(hits) and all(r.transporter.contains(g) for g in hits)
        for _ in range(10):
            p=tuple(int(x) for x in rng.permutation(n)); assert r.transporter.contains(p)==(p in hits)


def test_s8_single_mark_uses_eight_images_not_40320_group_elements():
    gens=[(1,0,2,3,4,5,6,7),(1,2,3,4,5,6,7,0)]
    src=(1,0,0,0,0,0,0,0); tgt=(0,0,0,0,0,0,0,1)
    r=string_orbit_stabilizer_transporter(gens,src,tgt,max_images=16)
    assert r.status=='exact_transporter_coset'
    assert r.orbit_size==8
    assert r.stabilizer.order==5040
    assert r.transporter.subgroup.order==5040


def test_image_orbit_limit_is_fail_closed():
    gens=[(1,0,2,3,4,5,6,7),(1,2,3,4,5,6,7,0)]
    src=(1,1,1,1,0,0,0,0)
    r=string_orbit_stabilizer_transporter(gens,src,max_images=10)
    assert r.status=='undetermined_image_orbit_limit'
    assert r.stabilizer is None and r.transporter is None
