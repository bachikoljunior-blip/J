import numpy as np
from hybrid_attributed_isomorphism import hybrid_attributed_isomorphism

def sparse_graph(n,seed=0,p=0.035):
    rng=np.random.default_rng(seed); r=rng.random((n,n)); upper=np.triu(r<p,1); a=upper|upper.T
    for i in range(n-1): a[i,i+1]=a[i+1,i]=True
    return a.astype(int)
def cycle(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    return a

def test_large_unique_attribute_relabeling():
    rng=np.random.default_rng(2); n=180; a=sparse_graph(n,3); x=rng.normal(size=(n,5)); p=rng.permutation(n)
    r=hybrid_attributed_isomorphism((a,x),(a[np.ix_(p,p)],x[p]),max_states=5000,rff_components=24,seed=4)
    assert r.status=="certified_isomorphic_exact" and r.isomorphic is True and r.explored_states<=n*2

def test_attribute_change_rejected_cheaply():
    rng=np.random.default_rng(5); a=sparse_graph(80,6); x=rng.normal(size=(80,4)); y=x.copy(); y[7]+=3.0
    r=hybrid_attributed_isomorphism((a,x),(a,y),max_states=1000,rff_components=32,seed=2)
    assert r.isomorphic is False and not r.used_exact_search

def test_symmetric_cycle_bounded_search():
    rng=np.random.default_rng(8); n=44; a=cycle(n); x=np.zeros((n,2)); p=rng.permutation(n)
    r=hybrid_attributed_isomorphism((a,x),(a[np.ix_(p,p)],x[p]),max_states=5000,rff_components=16,seed=1)
    assert r.status=="certified_isomorphic_exact" and r.isomorphic is True and r.explored_states<5000

def test_budget_exhaustion_fails_closed():
    rng=np.random.default_rng(9); n=18; a=cycle(n); x=np.zeros((n,2)); p=rng.permutation(n)
    r=hybrid_attributed_isomorphism((a,x),(a[np.ix_(p,p)],x[p]),max_states=1,rff_components=12,seed=1)
    assert r.status=="undetermined_budget_exhausted" and r.isomorphic is None and r.used_exact_search

def test_node_count_mismatch_no_search():
    r=hybrid_attributed_isomorphism((cycle(8),np.zeros((8,2))),(cycle(9),np.zeros((9,2))))
    assert r.isomorphic is False and not r.used_exact_search
