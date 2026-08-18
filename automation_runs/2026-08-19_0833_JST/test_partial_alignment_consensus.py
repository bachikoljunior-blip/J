import numpy as np
from partial_alignment_consensus import infer_partial_alignment_consensus

def path(n):
    a=np.zeros((n,n),dtype=int)
    for i in range(n-1): a[i,i+1]=a[i+1,i]=1
    return a
def cycle(n):
    a=path(n); a[0,n-1]=a[n-1,0]=1; return a
def test_permuted_plus_inserted_recovers_common_pairs():
    rng=np.random.default_rng(1); n=12; a=path(n); x=np.column_stack([np.arange(n),rng.normal(size=n)]); p=rng.permutation(n); bp=a[np.ix_(p,p)]; yp=x[p]; b=np.zeros((n+1,n+1),dtype=int); b[:n,:n]=bp; b[3,n]=b[n,3]=1; y=np.vstack([yp,np.array([[99.,7.]])]); inv=np.empty(n,dtype=int); inv[p]=np.arange(n); expected=tuple(sorted((i,int(inv[i])) for i in range(n))); r=infer_partial_alignment_consensus((a,x),(b,y),max_unmatched_total=1,max_common_edge_disagreements=0,max_states=50000); assert r.status=="unique_or_forced_consensus" and r.forced_pairs==expected and r.feasible_solutions==1
def test_symmetric_cycle_ambiguous():
    n=6; a=cycle(n); x=np.zeros((n,2)); r=infer_partial_alignment_consensus((a,x),(a,x),max_unmatched_total=0,max_common_edge_disagreements=0,max_states=100000); assert r.feasible_solutions==12 and r.status=="ambiguous_no_forced_pairs" and r.forced_pairs==()
def test_impossible_attribute_inventory():
    a=path(4); x=np.arange(8,dtype=float).reshape(4,2); y=x.copy(); y[3]+=100; r=infer_partial_alignment_consensus((a,x),(a,y),max_unmatched_total=0,max_common_edge_disagreements=0); assert r.status=="inconsistent_constraints" and r.forced_pairs==()
def test_tiny_budget_fails_closed():
    n=7; a=cycle(n); x=np.zeros((n,1)); r=infer_partial_alignment_consensus((a,x),(a,x),max_unmatched_total=0,max_common_edge_disagreements=0,max_states=3); assert r.status=="undetermined_budget_exhausted" and r.forced_pairs==()
def test_edge_disagreement_budget():
    n=8; a=path(n); x=np.column_stack([np.arange(n),np.arange(n)**2]); b=a.copy(); b[1,6]=b[6,1]=1; r0=infer_partial_alignment_consensus((a,x),(b,x),max_unmatched_total=0,max_common_edge_disagreements=0); r1=infer_partial_alignment_consensus((a,x),(b,x),max_unmatched_total=0,max_common_edge_disagreements=1); assert r0.status=="inconsistent_constraints" and len(r1.forced_pairs)==n and r1.feasible_solutions==1
