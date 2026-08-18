import numpy as np
from rff_stability_bounds import graph_feature_stability_certificate

def star(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(1,n): a[0,i]=a[i,0]=1
    return a
def complete_bipartite(p,q):
    n=p+q; a=np.zeros((n,n),dtype=int); a[:p,p:]=1; a[p:,:p]=1; return a
def random_graph(n,seed):
    rng=np.random.default_rng(seed); u=np.triu(rng.random((n,n))<.12,1); return (u|u.T).astype(int)
def check(a,x,y,**kw):
    c=graph_feature_stability_certificate(a,x,y,**kw); assert c.passed and c.actual_l2<=c.upper_bound_l2+1e-10; return c
def test_single_node_concentrated():
    rng=np.random.default_rng(10); a=star(61); x=rng.normal(size=(61,7)); y=x.copy(); y[0]+=np.array([5,-4,3,-2,1,.5,-.25]); check(a,x,y,iterations=5,rff_components=80,bandwidth=.7,seed=13)
def test_coherent_translation():
    rng=np.random.default_rng(11); a=complete_bipartite(25,30); x=rng.normal(size=(55,5)); y=x+np.array([2,-1,.5,3,-2.5]); check(a,x,y,iterations=4,rff_components=64,bandwidth=1.1,seed=14)
def test_large_magnitude():
    rng=np.random.default_rng(12); a=random_graph(45,2); x=rng.normal(size=(45,4)); y=x+rng.normal(scale=40,size=x.shape); check(a,x,y,iterations=3,rff_components=56,bandwidth=.4,seed=15)
def test_many_topologies_dimensions():
    rng=np.random.default_rng(13)
    for n,d in [(7,2),(19,3),(43,6),(87,8)]:
        a=random_graph(n,100+n); x=rng.normal(size=(n,d)); y=x+rng.uniform(-.4,.4,size=x.shape); check(a,x,y,iterations=2,rff_components=48,bandwidth=1.6,seed=16)
def test_bound_linear_in_perturbation_scale():
    rng=np.random.default_rng(14); a=star(30); x=rng.normal(size=(30,3)); direction=rng.normal(size=x.shape)
    c1=check(a,x,x+1e-4*direction,iterations=3,rff_components=40,bandwidth=1.0,seed=17); c2=check(a,x,x+2e-4*direction,iterations=3,rff_components=40,bandwidth=1.0,seed=17)
    assert np.isclose(c2.upper_bound_l2,2*c1.upper_bound_l2,rtol=1e-10,atol=1e-12)
