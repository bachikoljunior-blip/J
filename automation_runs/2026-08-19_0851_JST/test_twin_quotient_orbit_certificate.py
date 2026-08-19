import numpy as np

from twin_quotient_orbit_certificate import twin_quotient_orbit_certificate


def permute_graph(a,x,seed):
    p=np.random.default_rng(seed).permutation(len(a)); return (a[np.ix_(p,p)],x[p]),p


def test_large_uniform_clique_certifies_no_forced_pairs_from_one_verified_module():
    n=300; a=np.ones((n,n),dtype=int)-np.eye(n,dtype=int); x=np.zeros((n,1),dtype=float)
    gb,p=permute_graph(a,x,98)
    r=twin_quotient_orbit_certificate((a,x),gb)
    assert r.status=='certified_no_forced_pairs'
    assert r.forced_pairs==()
    assert r.source_modules==1 and r.target_modules==1


def test_large_star_forces_only_center_and_not_twin_leaves():
    n=401; a=np.zeros((n,n),dtype=int); a[0,1:]=1; a[1:,0]=1; x=np.zeros((n,1),dtype=float)
    gb,p=permute_graph(a,x,981); inv=np.empty(n,dtype=int); inv[p]=np.arange(n)
    r=twin_quotient_orbit_certificate((a,x),gb)
    assert r.status=='certified_exact_forced_pairs'
    assert r.source_modules==2 and r.target_modules==2
    assert r.forced_pairs==((0,int(inv[0])),)


def test_two_equal_twin_modules_can_certify_no_original_identity_even_if_quotient_swaps():
    # K_5,5 with identical attributes: two false-twin modules and a quotient edge.
    n=10; a=np.zeros((n,n),dtype=int); a[:5,5:]=1; a[5:,:5]=1; x=np.zeros((n,1),dtype=float)
    gb,p=permute_graph(a,x,982)
    r=twin_quotient_orbit_certificate((a,x),gb)
    assert r.status=='certified_no_forced_pairs'
    assert r.forced_pairs==()
