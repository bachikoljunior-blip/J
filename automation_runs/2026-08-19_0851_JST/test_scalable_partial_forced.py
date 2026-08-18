import numpy as np
from scalable_partial_forced import infer_attribute_capacity_forced

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

def brute_forced(a,x,b,y,ub,eb):
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
                    dis=sum(int(bool(a[pairs[q][0],pairs[r][0]])!=bool(b[pairs[q][1],pairs[r][1]])) for q in range(k) for r in range(q))
                    if dis<=eb: sols.append(set(pairs))
    if not sols:return set(),0
    z=set(sols[0])
    for s in sols[1:]: z&=s
    return z,len(sols)

def test_unique_attributes_plus_insertion_forces_common_pairs():
    rng=np.random.default_rng(1); n=80; a=path(n); x=np.arange(n,dtype=float)[:,None]; p=rng.permutation(n); bp=a[np.ix_(p,p)]; b=np.zeros((n+1,n+1),dtype=int); b[:n,:n]=bp; y=np.vstack([x[p],[[999.]]])
    r=infer_attribute_capacity_forced((a,x),(b,y),max_unmatched_total=1,max_common_edge_disagreements=0); inv=np.empty(n,dtype=int); inv[p]=np.arange(n)
    assert r.status=='certified_attribute_forced_pairs' and r.forced_pairs==tuple((i,int(inv[i])) for i in range(n))

def test_symmetric_duplicate_attributes_returns_no_pairs():
    a=path(10); x=np.zeros((10,1)); r=infer_attribute_capacity_forced((a,x),(a,x),max_unmatched_total=0,max_common_edge_disagreements=0); assert r.status=='feasible_no_attribute_forced_pairs' and r.forced_pairs==()

def test_random_small_returned_pairs_are_sound():
    rng=np.random.default_rng(12)
    for _ in range(700):
        n=int(rng.integers(1,5)); m=int(rng.integers(1,5)); a=graph_from_bits(n,int(rng.integers(0,1<<(n*(n-1)//2)))); b=graph_from_bits(m,int(rng.integers(0,1<<(m*(m-1)//2)))); x=rng.integers(0,3,size=(n,1)).astype(float); y=rng.integers(0,3,size=(m,1)).astype(float); ub=int(rng.integers(0,n+m+1)); eb=int(rng.integers(0,3))
        expected,count=brute_forced(a,x,b,y,ub,eb); r=infer_attribute_capacity_forced((a,x),(b,y),max_unmatched_total=ub,max_common_edge_disagreements=eb)
        if r.status=='certified_attribute_forced_pairs': assert count>0 and set(r.forced_pairs).issubset(expected)
