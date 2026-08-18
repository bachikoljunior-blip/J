import numpy as np
from structural_edit_stability import structural_edit_stability_certificate

def path(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(n-1): a[i,i+1]=a[i+1,i]=1
    return a
def cycle(n):
    a=path(n); a[0,n-1]=a[n-1,0]=1; return a
def test_single_far_chord():
    rng=np.random.default_rng(1); n=120; a=path(n); b=a.copy(); b[20,90]=b[90,20]=1; x=rng.normal(size=(n,4)); c=structural_edit_stability_certificate(a,b,x,iterations=3,rff_components=48,seed=4)
    assert c.edit_count==1 and c.support_validated and c.passed and c.support_sizes[0]==2 and c.support_sizes[-1]<n
def test_multiple_toggles():
    rng=np.random.default_rng(2); n=90; a=cycle(n); b=a.copy()
    for i,j in [(4,31),(17,63),(51,52)]: b[i,j]=1-b[i,j]; b[j,i]=b[i,j]
    c=structural_edit_stability_certificate(a,b,rng.normal(size=(n,5)),iterations=4,rff_components=64,bandwidth=.8,seed=5); assert c.edit_count==3 and c.support_validated and c.passed
def test_dense_union():
    rng=np.random.default_rng(3); n=45; u=np.triu(rng.random((n,n))<.25,1); a=(u|u.T).astype(int); b=a.copy(); b[0,1]=1-b[0,1]; b[1,0]=b[0,1]
    c=structural_edit_stability_certificate(a,b,rng.normal(size=(n,3)),iterations=3,rff_components=40,seed=6); assert c.support_validated and c.passed and c.support_sizes[-1]<=n
def test_no_edit_zero():
    rng=np.random.default_rng(4); a=cycle(30); c=structural_edit_stability_certificate(a,a.copy(),rng.normal(size=(30,2)),iterations=5,rff_components=24,seed=7)
    assert c.edit_count==0 and c.support_sizes==(0,0,0,0,0,0) and c.actual_feature_l2==0.0 and c.upper_bound_l2==0.0 and c.passed
def test_support_monotone():
    rng=np.random.default_rng(5); a=path(70); b=a.copy(); b[10,55]=b[55,10]=1; c=structural_edit_stability_certificate(a,b,rng.normal(size=(70,3)),iterations=6,rff_components=32,seed=8)
    assert c.support_validated and c.passed and all(u<=v for u,v in zip(c.support_sizes,c.support_sizes[1:]))
