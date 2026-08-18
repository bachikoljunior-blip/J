import numpy as np
from vertex_edit_stability import vertex_edit_stability_certificate

def graph_from_mask(n,mask):
    a=np.zeros((n,n),dtype=int); bit=0
    for i in range(n):
        for j in range(i+1,n):
            if (mask>>bit)&1: a[i,j]=a[j,i]=1
            bit+=1
    return a

def test_exhaustive_all_four_node_graphs_all_new_vertex_neighborhoods_and_reverse_deletions():
    n=4; edge_bits=n*(n-1)//2; x=np.array([[0.,0.],[1.,1.],[2.,4.],[3.,9.]])
    for mask in range(1<<edge_bits):
        a=graph_from_mask(n,mask)
        for neigh_mask in range(1<<n):
            b=np.zeros((n+1,n+1),dtype=int); b[:n,:n]=a
            for i in range(n):
                if (neigh_mask>>i)&1: b[i,n]=b[n,i]=1
            y=np.vstack([x,np.array([[7.,11.]])]); align=[(i,i) for i in range(n)]
            assert vertex_edit_stability_certificate((a,x),(b,y),align,iterations=2,rff_components=12,bandwidth=.9,seed=23).passed
            assert vertex_edit_stability_certificate((b,y),(a,x),[(i,i) for i in range(n)],iterations=2,rff_components=12,bandwidth=.9,seed=23).passed
