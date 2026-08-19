import itertools
import numpy as np
from anchorless_exact_symmetry import infer_anchorless_exact_forcing

def graph(n,edges):
    a=np.zeros((n,n),int)
    for u,v in edges:a[u,v]=a[v,u]=1
    return a,np.zeros((n,1),int)

def permute(g,p):
    a,x=g;p=np.asarray(p);return a[np.ix_(p,p)],x[p]

def oracle(g1,g2):
    a,x=g1;b,y=g2;n=len(a);sol=[]
    for p in itertools.permutations(range(n)):
        if any(tuple(x[i])!=tuple(y[p[i]]) for i in range(n)):continue
        if all(bool(a[i,j])==bool(b[p[i],p[j]]) for i in range(n) for j in range(i)):sol.append(p)
    if not sol:return set(),0
    return {(i,sol[0][i]) for i in range(n) if all(s[i]==sol[0][i] for s in sol)},len(sol)

def test_path_has_anchorless_globally_fixed_center():
    g=graph(5,[(0,1),(1,2),(2,3),(3,4)]);h=permute(g,[3,1,4,0,2]);c=infer_anchorless_exact_forcing(g,h);forced,count=oracle(g,h);assert set(c.forced_pairs)==forced and c.isomorphism_count==count and len(c.forced_pairs)==1

def test_cycle_correctly_releases_nothing_under_symmetry():
    g=graph(6,[(i,(i+1)%6) for i in range(6)]);h=permute(g,[2,5,1,4,0,3]);c=infer_anchorless_exact_forcing(g,h);assert c.status=='feasible_no_forced_pairs' and c.forced_pairs==() and c.isomorphism_count==12

def test_random_small_cases_match_independent_permutation_oracle():
    rng=np.random.default_rng(31)
    for _ in range(40):
        n=6;a=np.triu((rng.random((n,n))<.36).astype(int),1);a+=a.T;x=rng.integers(0,2,size=(n,1));p=rng.permutation(n);b=a[np.ix_(p,p)];y=x[p];c=infer_anchorless_exact_forcing((a,x),(b,y));forced,count=oracle((a,x),(b,y));assert set(c.forced_pairs)==forced and c.isomorphism_count==count

def test_cutoff_fails_closed():
    g=graph(8,[(i,(i+1)%8) for i in range(8)]);c=infer_anchorless_exact_forcing(g,g,max_search_nodes=2);assert c.status=='undetermined_search_budget' and c.forced_pairs==()
