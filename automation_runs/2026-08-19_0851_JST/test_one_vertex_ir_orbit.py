import numpy as np

from one_vertex_ir_orbit import exact_one_vertex_ir_orbit
from scalable_wl_alignment import infer_full_alignment_wl


def regular_asymmetric_example():
    n=12; a=np.zeros((n,n),dtype=int)
    edges=[(0,4),(0,5),(0,6),(1,3),(1,7),(1,8),(2,5),(2,6),(2,10),(3,6),(3,11),(4,5),(4,11),(7,9),(7,10),(8,9),(8,11),(9,10)]
    for u,v in edges: a[u,v]=a[v,u]=1
    return a,np.zeros((n,1),dtype=float)


def test_regular_graph_all_1wl_equal_but_one_vertex_ir_enumerates_unique_iso():
    a,x=regular_asymmetric_example(); n=len(a); p=np.random.default_rng(100).permutation(n); b=a[np.ix_(p,p)]; y=x[p]
    assert infer_full_alignment_wl((a,x),(b,y)).status=='ambiguous_or_refinement_insufficient'
    r=exact_one_vertex_ir_orbit((a,x),(b,y)); inv=np.empty(n,dtype=int); inv[p]=np.arange(n)
    assert r.status=='certified_exact_forced_pairs'
    assert r.isomorphism_count==1
    assert r.forced_pairs==tuple((i,int(inv[i])) for i in range(n))


def test_cycle_remains_nondiscrete_after_one_individualization_and_abstains():
    n=30; a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    x=np.zeros((n,1),dtype=float)
    r=exact_one_vertex_ir_orbit((a,x),(a,x),max_base_trials=4)
    assert r.status=='undetermined_refinement_depth'
    assert r.forced_pairs==()


def test_attribute_mismatch_is_inconsistent_without_identity_release():
    a,x=regular_asymmetric_example(); y=x.copy(); y[0,0]=1
    r=exact_one_vertex_ir_orbit((a,x),(a,y))
    assert r.status=='inconsistent_constraints'
    assert r.forced_pairs==()
