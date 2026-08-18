import numpy as np
from vertex_edit_stability import vertex_edit_stability_certificate

def path(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(n-1): a[i,i+1]=a[i+1,i]=1
    return a
def test_single_leaf_insertion():
    rng=np.random.default_rng(1); a=path(40); x=rng.normal(size=(40,4)); b=np.zeros((41,41),dtype=int); b[:40,:40]=a; b[12,40]=b[40,12]=1; y=np.vstack([x,rng.normal(size=(1,4))]); c=vertex_edit_stability_certificate((a,x),(b,y),[(i,i) for i in range(40)],iterations=3,rff_components=48,seed=7); assert c.inserted_nodes==1 and c.deleted_nodes==0 and c.passed
def test_vertex_deletion():
    rng=np.random.default_rng(2); a=path(35); x=rng.normal(size=(35,3)); keep=[i for i in range(35) if i!=17]; b=a[np.ix_(keep,keep)]; y=x[keep]; alignment=[(old,new) for new,old in enumerate(keep)]; c=vertex_edit_stability_certificate((a,x),(b,y),alignment,iterations=4,rff_components=40,seed=8); assert c.deleted_nodes==1 and c.inserted_nodes==0 and c.passed
def test_multiple_insertions():
    rng=np.random.default_rng(3); n=28; a=path(n); x=rng.normal(size=(n,5)); b=np.zeros((n+3,n+3),dtype=int); b[:n,:n]=a
    for u,v in [(3,n),(n,n+1),(n+1,n+2),(20,n+2)]: b[u,v]=b[v,u]=1
    y=np.vstack([x,rng.normal(size=(3,5))]); assert vertex_edit_stability_certificate((a,x),(b,y),[(i,i) for i in range(n)],iterations=3,rff_components=36,seed=9).passed
def test_permutation_plus_insertion():
    rng=np.random.default_rng(4); n=24; a=path(n); x=rng.normal(size=(n,2)); p=rng.permutation(n); bp=a[np.ix_(p,p)]; yp=x[p]; b=np.zeros((n+1,n+1),dtype=int); b[:n,:n]=bp; b[5,n]=b[n,5]=1; y=np.vstack([yp,rng.normal(size=(1,2))]); inv=np.empty(n,dtype=int); inv[p]=np.arange(n); alignment=[(i,int(inv[i])) for i in range(n)]; c=vertex_edit_stability_certificate((a,x),(b,y),alignment,iterations=3,rff_components=32,seed=10); assert c.common_nodes==n and c.inserted_nodes==1 and c.passed
def test_bad_alignment_attributes_fail_closed():
    a=path(5); x=np.arange(10,dtype=float).reshape(5,2); y=x.copy(); y[2,0]+=1
    try: vertex_edit_stability_certificate((a,x),(a,y),[(i,i) for i in range(5)],attribute_atol=0.0)
    except ValueError: pass
    else: raise AssertionError("mismatched aligned attributes must be rejected")
