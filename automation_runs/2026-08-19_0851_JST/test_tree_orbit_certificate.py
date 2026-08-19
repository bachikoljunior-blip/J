import numpy as np

from tree_orbit_certificate import exact_tree_orbit_certificate


def make_graph(n,edges,attrs=None):
    a=np.zeros((n,n),dtype=int)
    for u,v in edges: a[u,v]=a[v,u]=1
    if attrs is None: attrs=np.zeros(n,dtype=float)
    return a,np.asarray(attrs,dtype=float)[:,None]


def permute(g,seed):
    a,x=g; p=np.random.default_rng(seed).permutation(len(a)); return (a[np.ix_(p,p)],x[p]),p


def test_large_star_exact_orbits_force_only_center():
    n=500; g=make_graph(n,[(0,i) for i in range(1,n)]); gp,p=permute(g,101); inv=np.empty(n,dtype=int); inv[p]=np.arange(n)
    r=exact_tree_orbit_certificate(g,gp)
    assert r.status=='certified_exact_forced_pairs'
    assert r.forced_pairs==((0,int(inv[0])),)
    assert len(r.witness_pairs)==n


def test_path_has_expected_reflection_orbits_and_odd_center_forced():
    n=101; g=make_graph(n,[(i,i+1) for i in range(n-1)]); gp,p=permute(g,1011); inv=np.empty(n,dtype=int); inv[p]=np.arange(n)
    r=exact_tree_orbit_certificate(g,gp)
    assert r.status=='certified_exact_forced_pairs'
    assert r.forced_pairs==((n//2,int(inv[n//2])),)
    assert r.orbit_count==(n+1)//2


def test_repeated_attribute_asymmetric_tree_can_force_every_vertex():
    edges=[(0,1),(1,2),(2,3),(1,4),(4,5),(5,6),(5,7),(7,8)]
    attrs=[0,0,0,0,1,1,1,1,1]
    g=make_graph(9,edges,attrs); gp,p=permute(g,1012); inv=np.empty(9,dtype=int); inv[p]=np.arange(9)
    r=exact_tree_orbit_certificate(g,gp)
    assert r.status=='certified_exact_forced_pairs'
    assert r.forced_pairs==tuple((i,int(inv[i])) for i in range(9))
