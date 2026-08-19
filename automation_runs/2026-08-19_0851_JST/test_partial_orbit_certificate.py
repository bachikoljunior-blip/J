import numpy as np

from partial_orbit_certificate import bounded_partial_orbit_certificate


def cycle_with_inserted_isolated(n=8):
    a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    x=np.zeros((n,1),dtype=float)
    b0=np.zeros((n+1,n+1),dtype=int); b0[:n,:n]=a
    y0=np.zeros((n+1,1),dtype=float)
    p=np.random.default_rng(96).permutation(n+1)
    return (a,x),(b0[np.ix_(p,p)],y0[p])


def unique_inserted_case():
    n=8; a=np.zeros((n,n),dtype=int)
    edges=[(0,1),(0,2),(0,5),(0,6),(0,7),(1,2),(1,3),(1,5),(2,7),(3,5),(4,5),(4,6),(5,7),(6,7)]
    for u,v in edges: a[u,v]=a[v,u]=1
    attrs=np.array([0,2,3,2,1,3,1,0],dtype=float); x=attrs[:,None]
    b0=np.zeros((9,9),dtype=int); b0[:8,:8]=a
    for v in [0,2,6]: b0[8,v]=b0[v,8]=1
    y0=np.concatenate([attrs,[2.]])[:,None]
    p=np.array([6,0,8,5,4,7,1,3,2],dtype=int)
    return (a,x),(b0[np.ix_(p,p)],y0[p])


def test_partial_cycle_with_one_insertion_certifies_no_forced_identity():
    ga,gb=cycle_with_inserted_isolated()
    r=bounded_partial_orbit_certificate(ga,gb,max_unmatched_total=1,max_common_edge_disagreements=0)
    assert r.status=='certified_no_forced_pairs'
    assert r.forced_pairs==()
    assert r.witness_count>=2


def test_complete_bounded_enumeration_can_certify_exact_forced_set():
    ga,gb=unique_inserted_case()
    r=bounded_partial_orbit_certificate(ga,gb,max_unmatched_total=1,max_common_edge_disagreements=0)
    assert r.status=='certified_exact_forced_pairs'
    assert r.complete_enumeration
    assert len(r.forced_pairs)==8


def test_search_limit_is_fail_closed():
    ga,gb=cycle_with_inserted_isolated(10)
    r=bounded_partial_orbit_certificate(ga,gb,max_unmatched_total=1,max_common_edge_disagreements=0,max_states=1)
    assert r.status=='undetermined_search_limit'
    assert r.forced_pairs==()
