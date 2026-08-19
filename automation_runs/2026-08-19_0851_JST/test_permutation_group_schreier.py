from collections import deque
import itertools
import numpy as np

from permutation_group_schreier import (
    compose,group_orbit,identity,inverse,schreier_stabilizer_chain
)


def closure(gens):
    n=len(gens[0]); e=identity(n); seen={e}; q=deque([e])
    while q:
        x=q.popleft()
        for g in gens:
            y=compose(x,g)
            if y not in seen: seen.add(y); q.append(y)
    return seen


def test_s3_order_membership_and_orbit():
    gens=[(1,0,2),(1,2,0)]; c=schreier_stabilizer_chain(gens)
    assert c.order==6
    assert all(c.contains(p) for p in itertools.permutations(range(3)))
    assert group_orbit(c,0)==(0,1,2)


def test_cyclic_subgroup_rejects_nonmember():
    c=schreier_stabilizer_chain([(1,2,3,0)])
    assert c.order==4
    assert c.contains((2,3,0,1))
    assert not c.contains((1,0,2,3))


def test_random_small_chains_match_exhaustive_closure_order_membership_and_orbits():
    rng=np.random.default_rng(104)
    for _ in range(400):
        n=int(rng.integers(1,7)); ng=int(rng.integers(1,4)); gens=[]
        for _ in range(ng): gens.append(tuple(int(x) for x in rng.permutation(n)))
        exact=closure(gens); c=schreier_stabilizer_chain(gens)
        assert c.order==len(exact)
        for p in exact: assert c.contains(p)
        # Sample arbitrary permutations for rejection/acceptance consistency.
        for _ in range(10):
            p=tuple(int(x) for x in rng.permutation(n)); assert c.contains(p)==(p in exact)
        for point in range(n):
            exact_orbit=tuple(sorted({p[point] for p in exact}))
            assert group_orbit(c,point)==exact_orbit


def test_inverse_and_composition_identity():
    p=(2,0,3,1); e=identity(4)
    assert compose(p,inverse(p))==e and compose(inverse(p),p)==e
