import numpy as np
from finite_family_rff_certificate import matched_atomic_pair_count,exact_structural_rbf_kernel,approximate_structural_rff_kernel,finite_family_certificate

def path(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(n-1): a[i,i+1]=a[i+1,i]=1
    return a
def complete(n): return np.ones((n,n),dtype=int)-np.eye(n,dtype=int)
def test_single_pair():
    rng=np.random.default_rng(1); a=path(18); x=rng.normal(size=(18,3)); y=x+rng.normal(scale=.3,size=x.shape)
    c=finite_family_certificate([((a,x),(a,y))],iterations=3,rff_components=4096,bandwidth=1.2,seed=10,failure_probability=.05)
    assert c.total_atomic_comparisons>0 and c.pair_certificates[0].passed_realized_check
def test_shifted_family():
    rng=np.random.default_rng(2); pairs=[]
    for n in range(10,20):
        a=path(n); x=rng.normal(1.5,1.8,size=(n,4)); y=rng.normal(-1,2.2,size=(n,4)); pairs.append(((a,x),(a,y)))
    c=finite_family_certificate(pairs,iterations=2,rff_components=8192,bandwidth=1.5,seed=11,failure_probability=.05)
    assert all(p.passed_realized_check for p in c.pair_certificates)
    assert c.total_atomic_comparisons==sum(p.matched_atomic_pairs for p in c.pair_certificates)
def test_multiple_comparison_penalty():
    rng=np.random.default_rng(3); a=path(12); x=rng.normal(size=(12,2)); pair=((a,x),(a,x+.1))
    c1=finite_family_certificate([pair],iterations=2,rff_components=2048,seed=1,failure_probability=.05); c8=finite_family_certificate([pair]*8,iterations=2,rff_components=2048,seed=1,failure_probability=.05)
    assert c8.atomic_uniform_radius>c1.atomic_uniform_radius
def test_zero_matching_colors():
    rng=np.random.default_rng(4); a=path(8); b=complete(8); x=rng.normal(size=(8,3)); y=rng.normal(size=(8,3))
    assert matched_atomic_pair_count((a,x),(b,y),iterations=3)==0
    p=finite_family_certificate([((a,x),(b,y))],iterations=3,rff_components=128,seed=2).pair_certificates[0]
    assert p.exact_kernel==0.0 and p.approximate_kernel==0.0 and p.absolute_error_bound==0.0
def test_permutation_invariance():
    rng=np.random.default_rng(5); n=21; a=path(n); x=rng.normal(size=(n,5)); p=rng.permutation(n); b=a[np.ix_(p,p)]; y=x[p]
    assert np.isclose(exact_structural_rbf_kernel((a,x),(a,x),iterations=3,bandwidth=.8),exact_structural_rbf_kernel((a,x),(b,y),iterations=3,bandwidth=.8),atol=1e-12)
    assert np.isclose(approximate_structural_rff_kernel((a,x),(a,x),iterations=3,rff_components=512,bandwidth=.8,seed=3),approximate_structural_rff_kernel((a,x),(b,y),iterations=3,rff_components=512,bandwidth=.8,seed=3),atol=1e-10)
