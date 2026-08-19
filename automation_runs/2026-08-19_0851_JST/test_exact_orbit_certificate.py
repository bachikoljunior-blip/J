import numpy as np

from exact_orbit_certificate import exact_full_orbit_certificate


def make_cycle(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    return a,np.zeros((n,1),dtype=float)


def make_asymmetric_six():
    n=6; a=np.zeros((n,n),dtype=int)
    for u,v in [(0,2),(0,5),(1,2),(1,3),(1,4),(1,5),(2,3),(2,5)]: a[u,v]=a[v,u]=1
    return a,np.zeros((n,1),dtype=float)


def test_cycle_certifies_no_identity_is_forced_without_arbitrary_choice():
    a,x=make_cycle(10); p=np.random.default_rng(95).permutation(len(a)); b=a[np.ix_(p,p)]; y=x[p]
    r=exact_full_orbit_certificate((a,x),(b,y))
    assert r.status=='certified_no_forced_pairs'
    assert r.forced_pairs==()
    assert r.witness_count>=2


def test_asymmetric_graph_complete_enumeration_certifies_unique_mapping():
    a,x=make_asymmetric_six(); p=np.random.default_rng(951).permutation(len(a)); b=a[np.ix_(p,p)]; y=x[p]
    r=exact_full_orbit_certificate((a,x),(b,y))
    inv=np.empty(len(a),dtype=int); inv[p]=np.arange(len(a))
    assert r.status=='certified_exact_forced_pairs'
    assert r.complete_enumeration
    assert r.forced_pairs==tuple((i,int(inv[i])) for i in range(len(a)))


def test_tiny_state_limit_abstains_instead_of_releasing_unproven_pairs():
    a,x=make_cycle(12)
    r=exact_full_orbit_certificate((a,x),(a,x),max_states=1)
    assert r.status=='undetermined_search_limit'
    assert r.forced_pairs==()
