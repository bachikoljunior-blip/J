import numpy as np
from rff_stability_bounds import graph_feature_stability_certificate,rff_attribute_lipschitz,rff_atomic_hoeffding_radius,exact_rbf,approximate_rbf
from wl_attributed_kernel import RFFConfig

def path_graph(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(n-1): a[i,i+1]=a[i+1,i]=1
    return a
def random_sparse_graph(n,seed):
    rng=np.random.default_rng(seed); u=np.triu(rng.random((n,n))<0.05,1); a=u|u.T
    for i in range(n-1): a[i,i+1]=a[i+1,i]=1
    return a.astype(int)
def test_lipschitz_certificate_gaussian():
    rng=np.random.default_rng(1); a=path_graph(70); x=rng.normal(size=(70,5)); y=x+rng.normal(scale=.08,size=x.shape)
    c=graph_feature_stability_certificate(a,x,y,iterations=4,rff_components=64,bandwidth=1.3,seed=7); assert c.passed
def test_shifted_heavy_tail_cases():
    rng=np.random.default_rng(2)
    for case in range(20):
        a=random_sparse_graph(35,100+case); x=rng.normal(loc=-1.5,scale=2.2,size=(35,4)); noise=np.clip(rng.standard_t(3,size=x.shape),-8,8)*.12; y=x+.35+noise
        assert graph_feature_stability_certificate(a,x,y,iterations=3,rff_components=48,bandwidth=.9,seed=11).passed
def test_zero_perturbation():
    rng=np.random.default_rng(3); a=path_graph(20); x=rng.normal(size=(20,3)); c=graph_feature_stability_certificate(a,x,x.copy(),iterations=2,rff_components=20,seed=1)
    assert c.actual_l2==0.0 and c.upper_bound_l2==0.0 and c.passed
def test_atomic_rff_shift_pairs_within_declared_radius():
    rng=np.random.default_rng(4); m=4096; radius=rff_atomic_hoeffding_radius(m,.05)
    for seed in range(12):
        x=rng.normal(2,1.7,size=6); y=rng.normal(-1,2.4,size=6); cfg=RFFConfig(6,m,1.4,500+seed)
        assert abs(approximate_rbf(x,y,cfg)-exact_rbf(x,y,1.4))<=radius
def test_bandwidth_lipschitz_order():
    assert rff_attribute_lipschitz(RFFConfig(5,128,.5,6))>rff_attribute_lipschitz(RFFConfig(5,128,2.0,6))
