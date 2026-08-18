import numpy as np
from positive_budget_structural_forcing import infer_positive_budget_forcing

def make_graph():
    n=7; a=np.zeros((n,n),dtype=int); x=np.zeros((n,1)); x[:4,0]=[10,11,12,13]
    for t,pat in enumerate(((1,1,0,0),(0,0,1,1),(1,0,1,0)),start=4):
        for q,z in enumerate(pat):
            if z:a[t,q]=a[q,t]=1
    return a,x

def test_positive_budget_forces_duplicate_nodes_from_distant_anchor_patterns():
    a,x=make_graph(); p=np.random.default_rng(3).permutation(len(a)); b=a[np.ix_(p,p)]; y=x[p]; r=infer_positive_budget_forcing((a,x),(b,y),max_unmatched_total=0,max_common_edge_disagreements=1); inv=np.empty(len(a),dtype=int);inv[p]=np.arange(len(a)); assert r.status=='certified_forced_pairs' and r.forced_pairs==tuple((i,int(inv[i])) for i in range(len(a)))

def test_one_actual_edge_disagreement_allowed_and_verified():
    a,x=make_graph(); p=np.random.default_rng(5).permutation(len(a)); b=a[np.ix_(p,p)].copy(); y=x[p]; inv=np.empty(len(a),dtype=int);inv[p]=np.arange(len(a)); u,v=int(inv[4]),int(inv[0]); b[u,v]=b[v,u]=1-b[u,v]; r=infer_positive_budget_forcing((a,x),(b,y),max_unmatched_total=0,max_common_edge_disagreements=1); assert r.status=='certified_forced_pairs' and set(r.forced_pairs)==set((i,int(inv[i])) for i in range(len(a))) and r.edge_disagreements==1

def test_symmetric_case_can_abstain():
    n=8; a=np.zeros((n,n),dtype=int)
    for i in range(n): a[i,(i+1)%n]=a[(i+1)%n,i]=1
    x=np.zeros((n,1)); r=infer_positive_budget_forcing((a,x),(a,x),max_unmatched_total=0,max_common_edge_disagreements=1); assert r.forced_pairs==()
