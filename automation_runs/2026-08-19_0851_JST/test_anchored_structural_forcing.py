import numpy as np
from anchored_structural_forcing import infer_anchored_zero_edge_forcing

def path(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(n-1): a[i,i+1]=a[i+1,i]=1
    return a

def graph_from_bits(n,bits):
    a=np.zeros((n,n),dtype=int); k=0
    for i in range(n):
        for j in range(i+1,n):
            if (bits>>k)&1: a[i,j]=a[j,i]=1
            k+=1
    return a

def brute_forced(a,x,b,y,ub):
    from itertools import combinations,permutations
    import math
    n,m=len(a),len(b); kmin=max(0,math.ceil((n+m-ub)/2)); sols=[]
    for k in range(kmin,min(n,m)+1):
        if n+m-2*k>ub: continue
        for src in combinations(range(n),k):
            for dst in combinations(range(m),k):
                for perm in permutations(dst):
                    pairs=tuple(zip(src,perm))
                    if any(not np.array_equal(x[i],y[j]) for i,j in pairs): continue
                    ok=True
                    for q in range(k):
                        for r in range(q):
                            if bool(a[pairs[q][0],pairs[r][0]])!=bool(b[pairs[q][1],pairs[r][1]]): ok=False; break
                        if not ok: break
                    if ok: sols.append(set(pairs))
    if not sols:return set(),0
    z=set(sols[0])
    for s in sols[1:]: z&=s
    return z,len(sols)

def test_unique_endpoint_anchor_propagates_duplicate_path():
    n=14; a=path(n); x=np.zeros((n,1)); x[0,0]=9; p=np.random.default_rng(2).permutation(n); b=a[np.ix_(p,p)]; y=x[p]
    r=infer_anchored_zero_edge_forcing((a,x),(b,y),max_unmatched_total=0); inv=np.empty(n,dtype=int); inv[p]=np.arange(n)
    assert r.status=='certified_structural_forced_pairs' and r.forced_pairs==tuple((i,int(inv[i])) for i in range(n))

def test_anchorless_cycle_abstains():
    n=8; a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    x=np.zeros((n,1)); r=infer_anchored_zero_edge_forcing((a,x),(a,x),max_unmatched_total=0); assert r.status=='feasible_no_forced_pairs' and r.forced_pairs==()

def test_random_small_released_pairs_subset_exhaustive_oracle():
    rng=np.random.default_rng(44)
    for _ in range(500):
        n=int(rng.integers(1,5)); m=int(rng.integers(1,5)); a=graph_from_bits(n,int(rng.integers(0,1<<(n*(n-1)//2)))); b=graph_from_bits(m,int(rng.integers(0,1<<(m*(m-1)//2)))); x=rng.integers(0,3,size=(n,1)).astype(float); y=rng.integers(0,3,size=(m,1)).astype(float); ub=int(rng.integers(0,n+m+1))
        expected,count=brute_forced(a,x,b,y,ub); r=infer_anchored_zero_edge_forcing((a,x),(b,y),max_unmatched_total=ub)
        if r.status=='certified_structural_forced_pairs': assert count>0 and set(r.forced_pairs).issubset(expected)
