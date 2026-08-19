import numpy as np

from distance_profile_alignment import infer_full_alignment_distance_profiles


def graph_from_edges(n,edges,attrs=None):
    a=np.zeros((n,n),dtype=int)
    for u,v in edges: a[u,v]=a[v,u]=1
    if attrs is None: attrs=np.zeros(n,dtype=float)
    return a,np.asarray(attrs,dtype=float)[:,None]


def test_large_asymmetric_tree_metric_profiles_certify_permutation():
    # Main path plus deliberately unequal branch lengths creates exact metric
    # signatures without depending on floating point spectral calculations.
    n=120; edges=[(i,i+1) for i in range(89)]
    nxt=90
    for root,length in [(7,3),(19,5),(31,7),(44,4),(58,9),(73,6)]:
        prev=root
        for _ in range(length): edges.append((prev,nxt)); prev=nxt; nxt+=1
    # Attach remaining leaves asymmetrically.
    roots=[5,13,27,38,52,66,81]
    ri=0
    while nxt<n:
        edges.append((roots[ri%len(roots)],nxt)); nxt+=1; ri+=1
    a,x=graph_from_edges(n,edges)
    p=np.random.default_rng(99).permutation(n); b=a[np.ix_(p,p)]; y=x[p]
    r=infer_full_alignment_distance_profiles((a,x),(b,y))
    inv=np.empty(n,dtype=int); inv[p]=np.arange(n)
    assert r.status=='certified_unique_alignment'
    assert r.pairs==tuple((i,int(inv[i])) for i in range(n))


def test_uniform_cycle_metric_symmetry_abstains():
    n=50; edges=[(i,(i+1)%n) for i in range(n)]; a,x=graph_from_edges(n,edges)
    r=infer_full_alignment_distance_profiles((a,x),(a,x))
    assert r.status=='ambiguous_or_invariant_insufficient'
    assert r.pairs==()


def test_nonisomorphic_profile_inventory_difference_releases_nothing():
    a,x=graph_from_edges(6,[(0,1),(1,2),(2,3),(3,4),(4,5)])
    b,y=graph_from_edges(6,[(0,1),(0,2),(0,3),(0,4),(0,5)])
    r=infer_full_alignment_distance_profiles((a,x),(b,y))
    assert r.status=='inconsistent_constraints'
    assert r.pairs==()
