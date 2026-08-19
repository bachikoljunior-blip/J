import itertools,time
import numpy as np
from combined_structural_budget_lb import infer_combined_structural_lower_bound

def exact_min(a,x,b,y,U):
    n,m=len(a),len(b);k=max(0,(n+m-U+1)//2);best=None
    for sa in itertools.combinations(range(n),k):
        for sb in itertools.combinations(range(m),k):
            for perm in itertools.permutations(sb):
                if any(tuple(x[sa[t]])!=tuple(y[perm[t]]) for t in range(k)):continue
                d=0
                for p in range(k):
                    for q in range(p):d+=int(bool(a[sa[p],sa[q]])!=bool(b[perm[p],perm[q]]))
                best=d if best is None else min(best,d)
    return best

def g(n,edges,attrs=None):
    a=np.zeros((n,n),int)
    for u,v in edges:a[u,v]=a[v,u]=1
    if attrs is None:attrs=np.zeros((n,1),int)
    return a,np.asarray(attrs).reshape(n,-1)

def test_degree_regular_symmetry_broken_by_triangle_bound():
    c6=g(6,[(i,(i+1)%6) for i in range(6)]);tt=g(6,[(0,1),(1,2),(2,0),(3,4),(4,5),(5,3)])
    c=infer_combined_structural_lower_bound(c6,tt,max_unmatched_total=0,max_common_edge_disagreements=0)
    assert c.degree_lower_bound==0 and c.triangle_lower_bound==1 and c.inconsistent

def test_exhaustive_soundness_with_multiple_attribute_buckets():
    rng=np.random.default_rng(19);checked=0
    for _ in range(180):
        n=m=4;a=np.triu((rng.random((n,n))<.45).astype(int),1);a+=a.T;b=np.triu((rng.random((m,m))<.45).astype(int),1);b+=b.T;x=rng.integers(0,2,size=(n,1));y=rng.integers(0,2,size=(m,1));U=int(rng.integers(0,5));exact=exact_min(a,x,b,y,U);c=infer_combined_structural_lower_bound((a,x),(b,y),max_unmatched_total=U)
        if exact is None:assert c.inconsistent
        else:checked+=1;assert c.combined_lower_bound<=exact
    assert checked>40

def test_large_multibucket_planted_partial_alignment_is_not_falsely_rejected():
    rng=np.random.default_rng(23);n=80;extra=4;a=np.triu((rng.random((n,n))<.055).astype(int),1);a+=a.T;x=(np.arange(n)%8)[:,None];perm=rng.permutation(n);common=a[np.ix_(perm,perm)].copy();flips=[]
    while len(flips)<12:
        i,j=sorted(rng.choice(n,2,replace=False))
        if (i,j) not in flips:flips.append((i,j));common[i,j]^=1;common[j,i]^=1
    b=np.zeros((n+extra,n+extra),int);b[:n,:n]=common
    y=np.vstack([x[perm],(100+np.arange(extra))[:,None]])
    t0=time.perf_counter();c=infer_combined_structural_lower_bound((a,x),(b,y),max_unmatched_total=extra,max_common_edge_disagreements=12);elapsed=time.perf_counter()-t0
    assert c.minimum_common_nodes==80 and c.attribute_capacity==80 and c.combined_lower_bound<=12 and not c.inconsistent and elapsed<5.0
