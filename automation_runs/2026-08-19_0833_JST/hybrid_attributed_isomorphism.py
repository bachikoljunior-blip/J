from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
from surrogate_collision_audit import audit_surrogate_pair

@dataclass(frozen=True)
class HybridIsoResult:
    status: str
    isomorphic: Optional[bool]
    permutation: Optional[Tuple[int, ...]]
    explored_states: int
    used_exact_search: bool
    reason: str

def _validate_graph(graph):
    a=(np.asarray(graph[0])!=0); x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1]: raise ValueError("adjacency must be square")
    if not np.array_equal(a,a.T) or np.any(np.diag(a)): raise ValueError("expected simple undirected graph")
    if x.ndim!=2 or x.shape[0]!=a.shape[0] or x.shape[1]==0: raise ValueError("bad attribute shape")
    if not np.all(np.isfinite(x)): raise ValueError("non-finite attributes")
    return a,x

def hybrid_attributed_isomorphism(graph_a, graph_b, *, max_states=100000,
                                   attribute_atol=1e-10, iterations=4,
                                   rff_components=32, seed=0):
    if max_states<1: raise ValueError("max_states must be positive")
    if attribute_atol<0: raise ValueError("attribute_atol must be non-negative")
    a,x=_validate_graph(graph_a); b,y=_validate_graph(graph_b)
    if a.shape[0]!=b.shape[0] or x.shape[1]!=y.shape[1]:
        return HybridIsoResult("certified_nonisomorphic_shape",False,None,0,False,"shape differs")
    audit=audit_surrogate_pair((a,x),(b,y),iterations=iterations,rff_components=rff_components,seed=seed)
    if audit.status=="certified_distinct_by_invariant":
        return HybridIsoResult("certified_nonisomorphic_surrogate",False,None,0,False,audit.reason)
    if audit.status=="surrogate_collision_detected":
        return HybridIsoResult("certified_nonisomorphic_fingerprint",False,None,0,False,audit.reason)
    n=a.shape[0]; da=a.sum(1).astype(int); db=b.sum(1).astype(int)
    attr_ok=np.max(np.abs(x[:,None,:]-y[None,:,:]),axis=2)<=attribute_atol
    pa=[tuple(sorted(int(da[j]) for j in np.flatnonzero(a[i]))) for i in range(n)]
    pb=[tuple(sorted(int(db[j]) for j in np.flatnonzero(b[i]))) for i in range(n)]
    candidates=[]
    for i in range(n):
        c=[j for j in range(n) if attr_ok[i,j] and da[i]==db[j] and pa[i]==pb[j]]
        if not c:
            return HybridIsoResult("certified_nonisomorphic_vertex_invariants",False,None,0,False,"no compatible target")
        candidates.append(c)
    mapping=np.full(n,-1,dtype=int); used=np.zeros(n,dtype=bool); explored=0; exhausted=False
    def feasible(i,j):
        mapping[i]=j; used[j]=True; mapped=np.flatnonzero(mapping>=0); tgt=mapping[mapped]
        for u in range(n):
            if mapping[u]>=0: continue
            if not any((not used[v]) and np.array_equal(a[u,mapped],b[v,tgt]) for v in candidates[u]):
                mapping[i]=-1; used[j]=False; return False
        mapping[i]=-1; used[j]=False; return True
    def choose():
        mapped=np.flatnonzero(mapping>=0); tgt=mapping[mapped]; best_i=-1; best=None
        for i in range(n):
            if mapping[i]>=0: continue
            valid=[j for j in candidates[i] if not used[j] and (mapped.size==0 or np.array_equal(a[i,mapped],b[j,tgt]))]
            if best is None or len(valid)<len(best):
                best_i,best=i,valid
                if len(valid)<=1: break
        return best_i,([] if best is None else best)
    def dfs(depth):
        nonlocal explored,exhausted
        if depth==n: return True
        i,valid=choose()
        if not valid: return False
        for j in valid:
            explored+=1
            if explored>max_states: exhausted=True; return None
            if not feasible(i,j): continue
            mapping[i]=j; used[j]=True
            out=dfs(depth+1)
            if out is True: return True
            mapping[i]=-1; used[j]=False
            if out is None: return None
        return False
    out=dfs(0)
    if out is None or exhausted:
        return HybridIsoResult("undetermined_budget_exhausted",None,None,explored,True,"exact refinement budget exhausted")
    if out is False:
        return HybridIsoResult("certified_nonisomorphic_exact",False,None,explored,True,"all compatible mappings refuted")
    perm=tuple(int(v) for v in mapping); p=np.asarray(perm,dtype=int)
    if not np.array_equal(a,b[np.ix_(p,p)]) or np.max(np.abs(x-y[p]))>attribute_atol:
        raise RuntimeError("internal mapping verification failed")
    return HybridIsoResult("certified_isomorphic_exact",True,perm,explored,True,"complete preserving bijection found")
