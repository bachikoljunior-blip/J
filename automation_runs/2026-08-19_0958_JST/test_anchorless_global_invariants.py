import itertools,time
import numpy as np
from anchorless_global_invariants import infer_anchorless_invariant_forcing

def oracle(a,x,b,y):
    n=len(a);sol=[]
    for p in itertools.permutations(range(n)):
        if any(tuple(x[i])!=tuple(y[p[i]]) for i in range(n)):continue
        if all(bool(a[i,j])==bool(b[p[i],p[j]]) for i in range(n) for j in range(i)):sol.append(p)
    if not sol:return set()
    return {(i,sol[0][i]) for i in range(n) if all(s[i]==sol[0][i] for s in sol)}

def test_random_small_releases_are_oracle_forced():
    rng=np.random.default_rng(41)
    for _ in range(35):
        n=6;a=np.triu((rng.random((n,n))<.38).astype(int),1);a+=a.T;x=rng.integers(0,2,size=(n,1));p=rng.permutation(n);b=a[np.ix_(p,p)];y=x[p];c=infer_anchorless_invariant_forcing((a,x),(b,y));assert set(c.forced_pairs)<=oracle(a,x,b,y)

def test_large_random_graph_maps_without_factorial_enumeration():
    rng=np.random.default_rng(42);n=120;a=np.triu((rng.random((n,n))<.07).astype(int),1);a+=a.T;x=np.zeros((n,1),int);p=rng.permutation(n);b=a[np.ix_(p,p)];y=x[p];t0=time.perf_counter();c=infer_anchorless_invariant_forcing((a,x),(b,y),max_search_nodes=10000);elapsed=time.perf_counter()-t0;assert c.status=='certified_forced_pairs' and len(c.forced_pairs)>=100 and c.explored_nodes<10000 and elapsed<5.0

def test_large_cycle_abstains_on_identity_despite_finding_witness():
    n=80;a=np.zeros((n,n),int)
    for i in range(n):a[i,(i+1)%n]=a[(i+1)%n,i]=1
    x=np.zeros((n,1),int);p=np.roll(np.arange(n),17);b=a[np.ix_(p,p)];c=infer_anchorless_invariant_forcing((a,x),(b,x),max_search_nodes=20000);assert c.status=='feasible_no_forced_pairs' and c.forced_pairs==() and len(c.witness_pairs)==n

def test_nonisomorphic_same_degree_inventory_is_rejected_or_abstained_without_release():
    n=6;c6=np.zeros((n,n),int);tt=np.zeros((n,n),int)
    for i in range(n):c6[i,(i+1)%n]=c6[(i+1)%n,i]=1
    for tri in [(0,1,2),(3,4,5)]:
        for i,j in itertools.combinations(tri,2):tt[i,j]=tt[j,i]=1
    x=np.zeros((n,1),int);c=infer_anchorless_invariant_forcing((c6,x),(tt,x));assert c.status=='inconsistent_constraints' and c.forced_pairs==()
