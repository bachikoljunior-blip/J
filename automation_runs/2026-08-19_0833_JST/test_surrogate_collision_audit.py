import numpy as np
from surrogate_collision_audit import audit_surrogate_pair, structural_fingerprint


def cycle(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    return a

def disjoint_triangles():
    a=np.zeros((6,6),dtype=int)
    for off in [0,3]:
        for i,j in [(0,1),(1,2),(2,0)]: a[off+i,off+j]=a[off+j,off+i]=1
    return a

def triangular_prism():
    a=disjoint_triangles()
    for i in range(3): a[i,i+3]=a[i+3,i]=1
    return a

def k33():
    a=np.zeros((6,6),dtype=int)
    for i in range(3):
        for j in range(3,6): a[i,j]=a[j,i]=1
    return a

def test_c6_vs_two_triangles_collision_flagged():
    x=np.zeros((6,2)); r=audit_surrogate_pair((cycle(6),x),(disjoint_triangles(),x),iterations=4,rff_components=16,seed=1)
    assert r.surrogate_equal and r.status=="surrogate_collision_detected" and r.require_escalation
    assert "component_sizes" in r.differing_invariants and "triangles" in r.differing_invariants

def test_prism_vs_k33_collision_flagged():
    x=np.ones((6,3))*0.25; r=audit_surrogate_pair((triangular_prism(),x),(k33(),x),iterations=5,rff_components=20,seed=2)
    assert r.surrogate_equal and r.status=="surrogate_collision_detected" and "triangles" in r.differing_invariants

def test_matching_case_fails_closed():
    rng=np.random.default_rng(4); a=cycle(10); x=rng.normal(size=(10,4)); p=rng.permutation(10)
    r=audit_surrogate_pair((a,x),(a[np.ix_(p,p)],x[p]),iterations=3,rff_components=24,seed=3)
    assert r.surrogate_equal and r.status=="undetermined_fail_closed" and r.require_escalation

def test_feature_difference_safe_distinction():
    rng=np.random.default_rng(8); a=cycle(12); x=rng.normal(size=(12,2)); y=x.copy(); y[0]+=7.0
    r=audit_surrogate_pair((a,x),(a,y),iterations=3,rff_components=32,seed=5)
    assert (not r.surrogate_equal) and r.status=="certified_distinct_by_invariant" and not r.require_escalation

def test_fingerprint_permutation_invariant():
    rng=np.random.default_rng(9); a=triangular_prism(); p=rng.permutation(6)
    assert structural_fingerprint(a)==structural_fingerprint(a[np.ix_(p,p)])
