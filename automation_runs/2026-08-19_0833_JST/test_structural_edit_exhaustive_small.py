import numpy as np
from structural_edit_stability import structural_edit_stability_certificate

def adjacency_from_mask(n,mask):
    a=np.zeros((n,n),dtype=int); bit=0
    for i in range(n):
        for j in range(i+1,n):
            if (mask>>bit)&1: a[i,j]=a[j,i]=1
            bit+=1
    return a

def test_exhaustive_all_five_node_graphs_each_single_edge_toggle():
    n=5; pairs=[(i,j) for i in range(n) for j in range(i+1,n)]; x=np.array([[i,i*i,-i] for i in range(n)],dtype=float)
    for mask in range(1<<len(pairs)):
        a=adjacency_from_mask(n,mask)
        for i,j in pairs:
            b=a.copy(); b[i,j]=1-b[i,j]; b[j,i]=b[i,j]
            c=structural_edit_stability_certificate(a,b,x,iterations=2,rff_components=12,bandwidth=1.1,seed=19)
            assert c.edit_count==1 and c.support_validated and c.passed
