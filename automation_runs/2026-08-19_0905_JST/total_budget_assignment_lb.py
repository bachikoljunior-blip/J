from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple, Optional
from collections import defaultdict
import heapq, math
import numpy as np

@dataclass(frozen=True)
class BudgetAssignmentCertificate:
    status: str
    forced_pairs: Tuple[Tuple[int, int], ...]
    witness_pairs: Tuple[Tuple[int, int], ...]
    minimum_common_nodes: int
    lower_bound_disagreements: int
    witness_disagreements: int
    reason: str

def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)): raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)): raise ValueError('bad attributes')
    return a,x

def _key(row): return np.ascontiguousarray(row,dtype=np.float64).tobytes()

def _minimum_cost_k_matching(left:Iterable[int],right:Iterable[int],edge_cost:Dict[Tuple[int,int],int],k:int,*,forbidden:Optional[Tuple[int,int]]=None):
    left=tuple(left); right=tuple(right)
    if k<0 or k>min(len(left),len(right)): return None,()
    if k==0:return 0,()
    S=0; lnode={u:1+i for i,u in enumerate(left)}; rnode={v:1+len(left)+i for i,v in enumerate(right)}; T=1+len(left)+len(right); N=T+1; g=[[] for _ in range(N)]
    def add_edge(u,v,cap,cost,tag=None):
        g[u].append([v,len(g[v]),cap,int(cost),tag]); g[v].append([u,len(g[u])-1,0,-int(cost),None])
    for u in left:add_edge(S,lnode[u],1,0)
    for v in right:add_edge(rnode[v],T,1,0)
    for (u,v),c in edge_cost.items():
        if u not in lnode or v not in rnode or forbidden==(u,v):continue
        if c<0:raise ValueError('edge costs must be nonnegative')
        add_edge(lnode[u],rnode[v],1,int(c),(u,v))
    potential=[0]*N; flow=0; total=0
    while flow<k:
        inf=10**18; dist=[inf]*N; prev=[None]*N; dist[S]=0; pq=[(0,S)]
        while pq:
            d,u=heapq.heappop(pq)
            if d!=dist[u]:continue
            for ei,e in enumerate(g[u]):
                v,rev,cap,cost,tag=e
                if cap<=0:continue
                nd=d+cost+potential[u]-potential[v]
                if nd<dist[v]:dist[v]=nd;prev[v]=(u,ei);heapq.heappush(pq,(nd,v))
        if dist[T]==inf:return None,()
        for v in range(N):
            if dist[v]<inf:potential[v]+=dist[v]
        v=T; path_cost=0
        while v!=S:
            u,ei=prev[v]; e=g[u][ei]; path_cost+=e[3]; e[2]-=1; g[v][e[1]][2]+=1; v=u
        total+=path_cost; flow+=1
    matching=[]
    for u in left:
        for e in g[lnode[u]]:
            if e[4] is not None and e[2]==0:matching.append(e[4])
    return int(total),tuple(sorted(matching))

def _disagreements(a,b,pairs):
    d=0;pairs=tuple(pairs)
    for q in range(len(pairs)):
        i,j=pairs[q]
        for r in range(q):
            u,v=pairs[r];d+=int(bool(a[i,u])!=bool(b[j,v]))
    return d

def infer_total_budget_forcing(graph_a,graph_b,*,max_unmatched_total:int,max_common_edge_disagreements:int,max_exclusion_checks:int=4000):
    if max_unmatched_total<0 or max_common_edge_disagreements<0 or max_exclusion_checks<1:raise ValueError('bad budgets')
    a,x=_validate(graph_a);b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:return BudgetAssignmentCertificate('inconsistent_constraints',(),(),0,0,0,'attribute dimensions differ')
    n,m=len(a),len(b);k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m):return BudgetAssignmentCertificate('inconsistent_constraints',(),(),k,0,0,'unmatched budget impossible')
    aa,bb=defaultdict(list),defaultdict(list)
    for i in range(n):aa[_key(x[i])].append(i)
    for j in range(m):bb[_key(y[j])].append(j)
    keys=set(aa)|set(bb);cap=sum(min(len(aa[q]),len(bb[q])) for q in keys)
    if cap<k:return BudgetAssignmentCertificate('inconsistent_constraints',(),(),k,0,0,'attribute inventory cannot reach minimum common nodes')
    anchors={}
    for q in keys:
        if len(aa[q])==1 and len(bb[q])==1 and cap-1<k:anchors[aa[q][0]]=bb[q][0]
    ap=tuple(sorted(anchors.items()));base=_disagreements(a,b,ap)
    if base>max_common_edge_disagreements:return BudgetAssignmentCertificate('inconsistent_constraints',(),(),k,base,base,'forced anchors alone exceed edge budget')
    left=[i for i in range(n) if i not in anchors];used=set(anchors.values());right=[j for j in range(m) if j not in used];need=max(0,k-len(anchors));cost={}
    for i in left:
        for j in bb.get(_key(x[i]),()):
            if j in used:continue
            d=sum(int(bool(a[i,u])!=bool(b[j,v])) for u,v in ap)
            if base+d<=max_common_edge_disagreements:cost[(i,j)]=d
    min_extra,match=_minimum_cost_k_matching(left,right,cost,need)
    if min_extra is None:return BudgetAssignmentCertificate('inconsistent_constraints',(),(),k,0,0,'same-attribute candidate graph cannot reach minimum common nodes')
    lower_bound=base+min_extra
    if lower_bound>max_common_edge_disagreements:return BudgetAssignmentCertificate('inconsistent_constraints',(),(),k,lower_bound,0,'minimum aggregate anchor-disagreement assignment already exceeds total edge budget')
    witness=tuple(sorted(ap+match))
    if len(witness)<k or n+m-2*len(witness)>max_unmatched_total:return BudgetAssignmentCertificate('undetermined_no_witness',(),(),k,lower_bound,0,'lower-bound matching misses unmatched budget')
    for i,j in witness:
        if not np.array_equal(x[i],y[j]):return BudgetAssignmentCertificate('undetermined_no_witness',(),(),k,lower_bound,0,'witness attribute mismatch')
    witness_dis=_disagreements(a,b,witness)
    if witness_dis>max_common_edge_disagreements:return BudgetAssignmentCertificate('undetermined_no_witness',(),(),k,lower_bound,witness_dis,'minimum-lower-bound witness exceeds full edge budget; no identities released')
    forced=list(ap);checks=0
    for e in match:
        if checks>=max_exclusion_checks:return BudgetAssignmentCertificate('undetermined_check_budget',tuple(sorted(ap)),witness,k,lower_bound,witness_dis,'exclusion-check budget exceeded; only inventory anchors released')
        checks+=1;alt_cost,_=_minimum_cost_k_matching(left,right,cost,need,forbidden=e)
        if alt_cost is None or base+alt_cost>max_common_edge_disagreements:forced.append(e)
    return BudgetAssignmentCertificate('certified_forced_pairs' if forced else 'feasible_no_forced_pairs',tuple(sorted(forced)),witness,k,lower_bound,witness_dis,'forced pairs proven by inventory necessity or exclusion under a global aggregate assignment lower bound; witness directly verified')
