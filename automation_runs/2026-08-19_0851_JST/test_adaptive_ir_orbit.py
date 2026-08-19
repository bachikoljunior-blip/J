import numpy as np

from adaptive_ir_orbit import exact_adaptive_ir_orbit


def cycle(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    return a,np.zeros((n,1),dtype=float)


def regular_example():
    n=12; a=np.zeros((n,n),dtype=int)
    for u,v in [(0,4),(0,5),(0,6),(1,3),(1,7),(1,8),(2,5),(2,6),(2,10),(3,6),(3,11),(4,5),(4,11),(7,9),(7,10),(8,9),(8,11),(9,10)]: a[u,v]=a[v,u]=1
    return a,np.zeros((n,1),dtype=float)


def test_cycle_complete_ir_finds_empty_forced_intersection():
    a,x=cycle(12); p=np.random.default_rng(102).permutation(len(a)); b=a[np.ix_(p,p)]; y=x[p]
    r=exact_adaptive_ir_orbit((a,x),(b,y),max_states=10000)
    assert r.status=='certified_no_forced_pairs'
    assert r.witness_count>=2
    assert r.forced_pairs==()


def test_regular_asymmetric_graph_complete_ir_certifies_unique_mapping():
    a,x=regular_example(); n=len(a); p=np.random.default_rng(1021).permutation(n); b=a[np.ix_(p,p)]; y=x[p]
    r=exact_adaptive_ir_orbit((a,x),(b,y)); inv=np.empty(n,dtype=int); inv[p]=np.arange(n)
    assert r.status=='certified_exact_forced_pairs'
    assert r.complete_enumeration
    assert r.witness_count==1
    assert r.forced_pairs==tuple((i,int(inv[i])) for i in range(n))


def test_tiny_state_limit_is_fail_closed():
    a,x=cycle(20)
    r=exact_adaptive_ir_orbit((a,x),(a,x),max_states=1)
    assert r.status=='undetermined_search_limit'
    assert r.forced_pairs==()
