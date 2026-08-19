from itertools import combinations, permutations
import math
import numpy as np

from anchorless_partial_global_lb import infer_anchorless_partial_global_lb


def direct_disagreements(a,b,w):
    d=0
    for q,(i,j) in enumerate(w):
        for u,v in w[:q]: d += int(bool(a[i,u]) != bool(b[j,v]))
    return d


def brute_forced(graph_a,graph_b,U,E):
    a,x=graph_a; b,y=graph_b; n=len(a); m=len(b)
    k=max(0,math.ceil((n+m-U)/2)); feasible=[]
    for kk in range(k,min(n,m)+1):
        for ls in combinations(range(n),kk):
            cand={i:[j for j in range(m) if np.array_equal(x[i],y[j])] for i in ls}
            order=sorted(ls,key=lambda i:len(cand[i])); assign={}; used=set()
            def rec(t):
                if t==len(order):
                    w=tuple(sorted(assign.items()))
                    if direct_disagreements(a,b,w)<=E: feasible.append(set(w))
                    return
                i=order[t]
                for j in cand[i]:
                    if j in used: continue
                    assign[i]=j; used.add(j); rec(t+1); used.remove(j); del assign[i]
            rec(0)
    if not feasible: return None,set()
    forced=set(feasible[0])
    for s in feasible[1:]: forced &= s
    return feasible,forced


def constructed_inserted_case():
    n=8; a=np.zeros((n,n),dtype=int)
    edges=[(0,1),(0,2),(0,5),(0,6),(0,7),(1,2),(1,3),(1,5),(2,7),(3,5),(4,5),(4,6),(5,7),(6,7)]
    for u,v in edges: a[u,v]=a[v,u]=1
    attrs=np.array([0,2,3,2,1,3,1,0],dtype=float)
    x=attrs[:,None]
    b0=np.zeros((9,9),dtype=int); b0[:8,:8]=a
    for v in [0,2,6]: b0[8,v]=b0[v,8]=1
    y0=np.concatenate([attrs,[2.]])[:,None]
    p=np.array([6,0,8,5,4,7,1,3,2],dtype=int)
    return (a,x),(b0[np.ix_(p,p)],y0[p])


def test_anchorless_global_lb_forces_pairs_with_one_insertion_and_no_identity_anchor():
    ga,gb=constructed_inserted_case()
    r=infer_anchorless_partial_global_lb(ga,gb,max_unmatched_total=1,max_common_edge_disagreements=0)
    assert r.status=='certified_forced_pairs'
    assert set(r.forced_pairs)=={(4,4),(6,0)}
    assert r.witness_edge_disagreements==0


def test_random_small_releases_are_subset_of_full_exhaustive_forced_set():
    rng=np.random.default_rng(9401); released=0
    for _ in range(800):
        n=int(rng.integers(2,5)); m=int(rng.integers(2,5))
        a=np.triu((rng.random((n,n))<0.4).astype(int),1); a=a+a.T
        b=np.triu((rng.random((m,m))<0.4).astype(int),1); b=b+b.T
        x=rng.integers(0,3,size=(n,1)).astype(float)
        y=rng.integers(0,3,size=(m,1)).astype(float)
        U=int(rng.integers(abs(n-m),n+m+1)); E=int(rng.integers(0,3))
        feasible,true_forced=brute_forced((a,x),(b,y),U,E)
        r=infer_anchorless_partial_global_lb((a,x),(b,y),max_unmatched_total=U,max_common_edge_disagreements=E)
        if r.forced_pairs:
            released += len(r.forced_pairs)
            assert feasible is not None
            assert set(r.forced_pairs).issubset(true_forced)
    assert released>0
