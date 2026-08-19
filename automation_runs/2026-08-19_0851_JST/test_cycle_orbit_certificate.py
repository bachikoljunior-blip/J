import numpy as np

from cycle_orbit_certificate import exact_cycle_orbit_certificate


def cycle_graph(n,attrs=None):
    a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    if attrs is None: attrs=np.zeros(n,dtype=float)
    return a,np.asarray(attrs,dtype=float)[:,None]


def test_large_uniform_cycle_certifies_no_forced_pairs_and_all_dihedral_maps():
    a,x=cycle_graph(500); p=np.random.default_rng(97).permutation(len(a)); b=a[np.ix_(p,p)]; y=x[p]
    r=exact_cycle_orbit_certificate((a,x),(b,y))
    assert r.status=='certified_no_forced_pairs'
    assert r.forced_pairs==()
    assert r.isomorphism_count==1000


def test_attribute_pattern_can_reduce_cycle_isomorphism_family_exactly():
    attrs=np.array([0,1,2,3,4,5,6,7],dtype=float)
    a,x=cycle_graph(8,attrs); p=np.array([3,6,0,7,4,1,5,2],dtype=int); b=a[np.ix_(p,p)]; y=x[p]
    r=exact_cycle_orbit_certificate((a,x),(b,y))
    inv=np.empty(len(a),dtype=int); inv[p]=np.arange(len(a))
    assert r.status=='certified_exact_forced_pairs'
    assert r.isomorphism_count==1
    assert r.forced_pairs==tuple((i,int(inv[i])) for i in range(len(a)))


def test_noncycle_is_not_applicable_fail_closed():
    a=np.zeros((5,5),dtype=int)
    for i in range(4): a[i,i+1]=a[i+1,i]=1
    x=np.zeros((5,1),dtype=float)
    r=exact_cycle_orbit_certificate((a,x),(a,x))
    assert r.status=='not_applicable'
    assert r.forced_pairs==()
