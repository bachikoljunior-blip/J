import heapq
import numpy as np

from distance_profile_alignment import infer_full_alignment_distance_profiles


def graph_from_edges(n,edges,attrs=None):
    a=np.zeros((n,n),dtype=int)
    for u,v in edges: a[u,v]=a[v,u]=1
    if attrs is None: attrs=np.zeros(n,dtype=float)
    return a,np.asarray(attrs,dtype=float)[:,None]


def deterministic_repeated_attribute_tree(n=140,seed=101):
    rng=np.random.default_rng(seed); prufer=rng.integers(0,n,size=n-2); deg=np.ones(n,dtype=int)
    for v in prufer: deg[int(v)]+=1
    leaves=[i for i,d in enumerate(deg) if d==1]; heapq.heapify(leaves); edges=[]
    for vv in prufer:
        v=int(vv); u=heapq.heappop(leaves); edges.append((u,v)); deg[u]-=1; deg[v]-=1
        if deg[v]==1: heapq.heappush(leaves,v)
    edges.append((heapq.heappop(leaves),heapq.heappop(leaves)))
    attrs=np.repeat(np.arange(14),10).astype(float); rng.shuffle(attrs)
    return graph_from_edges(n,edges,attrs)


def test_large_repeated_attribute_tree_metric_profiles_certify_permutation():
    # Every attribute value occurs 10 times, so identities are not supplied by
    # singleton attributes. Exact distance-to-attribute-bucket profiles separate
    # all 140 vertices in this deterministic tree.
    a,x=deterministic_repeated_attribute_tree()
    n=len(a); p=np.random.default_rng(99).permutation(n); b=a[np.ix_(p,p)]; y=x[p]
    r=infer_full_alignment_distance_profiles((a,x),(b,y))
    inv=np.empty(n,dtype=int); inv[p]=np.arange(n)
    assert r.status=='certified_unique_alignment'
    assert r.distinct_signatures==n
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
