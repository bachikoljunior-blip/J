import numpy as np

from scalable_2wl_alignment import infer_full_alignment_2wl
from scalable_wl_alignment import infer_full_alignment_wl


def regular_asymmetric_example():
    n=12; a=np.zeros((n,n),dtype=int)
    edges=[(0,4),(0,5),(0,6),(1,3),(1,7),(1,8),(2,5),(2,6),(2,10),(3,6),(3,11),(4,5),(4,11),(7,9),(7,10),(8,9),(8,11),(9,10)]
    for u,v in edges: a[u,v]=a[v,u]=1
    x=np.zeros((n,1),dtype=float)
    return a,x


def test_2wl_resolves_anchorless_regular_graph_that_1wl_abstains():
    a,x=regular_asymmetric_example(); p=np.random.default_rng(93).permutation(len(a)); b=a[np.ix_(p,p)]; y=x[p]
    r1=infer_full_alignment_wl((a,x),(b,y)); r2=infer_full_alignment_2wl((a,x),(b,y))
    assert r1.status=='ambiguous_or_refinement_insufficient'
    assert r2.status=='certified_unique_alignment'
    inv=np.empty(len(a),dtype=int); inv[p]=np.arange(len(a))
    assert r2.pairs==tuple((i,int(inv[i])) for i in range(len(a)))


def test_cycle_symmetry_remains_fail_closed():
    n=10; a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    x=np.zeros((n,1),dtype=float)
    r=infer_full_alignment_2wl((a,x),(a,x))
    assert r.status=='ambiguous_or_refinement_insufficient'
    assert r.pairs==()


def test_direct_verification_rejects_nonisomorphic_same_size_graphs():
    a,x=regular_asymmetric_example(); b=a.copy(); b[0,4]=b[4,0]=0; b[0,1]=b[1,0]=1
    r=infer_full_alignment_2wl((a,x),(b,x.copy()))
    assert r.status!='certified_unique_alignment'
    assert r.pairs==()
