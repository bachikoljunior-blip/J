import numpy as np
from anchorless_partial_budget_exact import infer_anchorless_partial_budget_forcing

def path(n):
    a=np.zeros((n,n),int)
    for i in range(n-1):a[i,i+1]=a[i+1,i]=1
    return a,np.zeros((n,1),int)
def permute(g,p):
    a,x=g;p=np.asarray(p);return a[np.ix_(p,p)],x[p]
def test_zero_budget_cycle_releases_nothing():
    n=6;a=np.zeros((n,n),int)
    for i in range(n):a[i,(i+1)%n]=a[(i+1)%n,i]=1
    x=np.zeros((n,1),int);c=infer_anchorless_partial_budget_forcing((a,x),(a,x),max_unmatched_total=0,max_common_edge_disagreements=0);assert c.forced_pairs==()
def test_positive_edge_budget_matches_known_feasible_mapping():
    g=path(5);h=permute(g,[3,1,4,0,2]);b,y=h;b=b.copy();b[0,1]^=1;b[1,0]^=1;c=infer_anchorless_partial_budget_forcing(g,(b,y),max_unmatched_total=0,max_common_edge_disagreements=1);assert c.feasible_mapping_count>0 and len(c.witness_pairs)==5
def test_partial_unique_distractor_retains_center():
    a,x=path(5);p=[2,4,0,3,1];bp=a[np.ix_(p,p)];yp=x[p];b=np.zeros((6,6),int);b[:5,:5]=bp;y=np.vstack([yp,[[99]]]);c=infer_anchorless_partial_budget_forcing((a,x),(b,y),max_unmatched_total=1,max_common_edge_disagreements=0);assert len(c.forced_pairs)==1
