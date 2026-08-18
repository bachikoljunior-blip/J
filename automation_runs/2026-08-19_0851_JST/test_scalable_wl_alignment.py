import numpy as np
from scalable_wl_alignment import infer_full_alignment_wl

def random_graph(seed,n,p=0.12):
    rng=np.random.default_rng(seed); tri=np.triu(rng.random((n,n))<p,1); return (tri|tri.T).astype(int)

def test_large_random_constant_attribute_graph_certifies_permutation():
    rng=np.random.default_rng(1); n=220; a=random_graph(2,n,0.08); x=np.zeros((n,1)); p=rng.permutation(n); b=a[np.ix_(p,p)]; y=x[p]
    r=infer_full_alignment_wl((a,x),(b,y),max_rounds=20); inv=np.empty(n,dtype=int); inv[p]=np.arange(n)
    assert r.status=='certified_unique_alignment',r
    assert r.pairs==tuple((i,int(inv[i])) for i in range(n))

def test_cycle_abstains_instead_of_fabricating_mapping():
    n=20; a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    x=np.zeros((n,1)); r=infer_full_alignment_wl((a,x),(a,x)); assert r.status=='ambiguous_or_refinement_insufficient' and r.pairs==()

def test_nonisomorphic_color_inventory_rejected():
    n=8; a=np.zeros((n,n),dtype=int)
    for i in range(n-1): a[i,i+1]=a[i+1,i]=1
    b=a.copy(); b[0,7]=b[7,0]=1; x=np.zeros((n,1)); r=infer_full_alignment_wl((a,x),(b,x)); assert r.status=='inconsistent_constraints' and r.pairs==()

def test_distinct_attribute_case_directly_verifies():
    n=50; a=random_graph(7,n,0.10); x=np.arange(n,dtype=float)[:,None]; p=np.random.default_rng(8).permutation(n); b=a[np.ix_(p,p)]; y=x[p]
    assert infer_full_alignment_wl((a,x),(b,y)).status=='certified_unique_alignment'
