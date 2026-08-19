from collections import deque
import numpy as np
from permutation_group_schreier import compose,identity,schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset,point_stabilizer_generators,pointwise_stabilizer_chain

def closure(gens):
    n=len(gens[0]); e=identity(n); seen={e}; q=deque([e])
    while q:
        x=q.popleft()
        for g in gens:
            y=compose(x,g)
            if y not in seen: seen.add(y); q.append(y)
    return seen

def test_random_point_and_pointwise_stabilizers_match_exhaustive_group_elements():
    rng=np.random.default_rng(105)
    for _ in range(300):
        n=int(rng.integers(1,7)); gens=[tuple(int(x) for x in rng.permutation(n)) for _ in range(int(rng.integers(1,4)))]
        exact=closure(gens); p=int(rng.integers(0,n)); sg=point_stabilizer_generators(gens,p); sexact={g for g in exact if g[p]==p}; sclosure=closure(sg or [identity(n)])
        assert sclosure==sexact
        pts=tuple(int(x) for x in rng.choice(n,size=int(rng.integers(0,n+1)),replace=False)); chain=schreier_stabilizer_chain(gens); pc=pointwise_stabilizer_chain(chain,pts); pexact={g for g in exact if all(g[z]==z for z in pts)}
        assert pc.order==len(pexact) and all(pc.contains(g) for g in pexact)

def test_right_coset_membership_matches_explicit_elements():
    rng=np.random.default_rng(1051)
    for _ in range(150):
        n=int(rng.integers(1,7)); gens=[tuple(int(x) for x in rng.permutation(n)) for _ in range(int(rng.integers(1,3)))]; subgroup=schreier_stabilizer_chain(gens); exact=closure(gens); rep=tuple(int(x) for x in rng.permutation(n)); cos=RightCoset(subgroup,rep); explicit={compose(rep,h) for h in exact}
        for _ in range(20):
            p=tuple(int(x) for x in rng.permutation(n)); assert cos.contains(p)==(p in explicit)
