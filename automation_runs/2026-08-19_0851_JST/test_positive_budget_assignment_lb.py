from itertools import combinations, permutations
import math
import numpy as np

from positive_budget_structural_forcing import infer_positive_budget_forcing


def direct_disagreements(a,b,w):
    d=0
    for q,(i,j) in enumerate(w):
        for u,v in w[:q]:
            d += int(bool(a[i,u]) != bool(b[j,v]))
    return d


def brute_forced(graph_a,graph_b,max_unmatched_total,budget):
    a,x=graph_a; b,y=graph_b; n=len(a); m=len(b)
    k=max(0,math.ceil((n+m-max_unmatched_total)/2)); feasible=[]
    for kk in range(k,min(n,m)+1):
        for ls in combinations(range(n),kk):
            for rs in combinations(range(m),kk):
                for p in permutations(rs):
                    w=tuple(zip(ls,p))
                    if not all(np.array_equal(x[i],y[j]) for i,j in w): continue
                    if direct_disagreements(a,b,w)<=budget: feasible.append(set(w))
    if not feasible: return None,set()
    forced=set(feasible[0])
    for s in feasible[1:]: forced &= s
    return feasible,forced


def test_total_anchor_assignment_bound_detects_collective_budget_failure():
    # Nodes 0 and 1 are capacity-critical unique-attribute anchors. Both
    # duplicate-attribute remaining nodes incur exactly one anchor mismatch under
    # every candidate pairing. Per-pair screening with budget=1 keeps all four
    # candidate edges, but any size-2 remaining assignment costs 2 in total.
    a=np.zeros((4,4),dtype=int); b=np.zeros((4,4),dtype=int)
    x=np.array([[10.],[11.],[0.],[0.]])
    y=x.copy()
    b[0,2]=b[2,0]=1; b[0,3]=b[3,0]=1
    r=infer_positive_budget_forcing((a,x),(b,y),max_unmatched_total=0,max_common_edge_disagreements=1)
    assert r.status=='inconsistent_constraints'
    assert 'assignment lower bound' in r.reason
    assert r.assignment_anchor_lower_bound==2


def test_random_small_released_pairs_are_true_forced_pairs_under_full_budget():
    rng=np.random.default_rng(9201); released=0
    for _ in range(500):
        n=int(rng.integers(2,5)); m=int(rng.integers(2,5))
        a=np.triu((rng.random((n,n))<0.35).astype(int),1); a=a+a.T
        b=np.triu((rng.random((m,m))<0.35).astype(int),1); b=b+b.T
        x=rng.integers(0,3,size=(n,1)).astype(float)
        y=rng.integers(0,3,size=(m,1)).astype(float)
        unmatched=int(rng.integers(abs(n-m),n+m+1)); budget=int(rng.integers(0,4))
        feasible,true_forced=brute_forced((a,x),(b,y),unmatched,budget)
        r=infer_positive_budget_forcing((a,x),(b,y),max_unmatched_total=unmatched,max_common_edge_disagreements=budget)
        if r.forced_pairs:
            released += len(r.forced_pairs)
            assert feasible is not None
            assert set(r.forced_pairs).issubset(true_forced)
    assert released>0
