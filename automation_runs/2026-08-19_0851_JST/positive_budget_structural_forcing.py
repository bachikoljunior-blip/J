from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict,deque
from typing import Tuple
import math,numpy as np

@dataclass(frozen=True)
class PositiveBudgetCertificate:
    status:str; forced_pairs:Tuple[Tuple[int,int],...]; witness_pairs:Tuple[Tuple[int,int],...]; minimum_common_nodes:int; candidate_matching_size:int; edge_disagreements:int; reason:str

def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)): raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)): raise ValueError('bad attributes')
    return a,x

def _key(row): return np.ascontiguousarray(row,dtype=np.float64).tobytes()

def _hk(adj,left,right,forbidden=None):
    pu={u:None for u in left}; pv={v:None for v in right}; dist={}
    def bfs():
        q=deque(); found=False
        for u in left:
            if pu[u] is None: dist[u]=0; q.append(u)
            else: dist[u]=-1
        while q:
            u=q.popleft()
            for v in adj.get(u,()):
                if forbidden==(u,v): continue
                z=pv.get(v)
                if z is None: found=True
                elif dist[z]<0: dist[z]=dist[u]+1; q.append(z)
        return found
    def dfs(u):
        for v in adj.get(u,()):
            if forbidden==(u,v): continue
            z=pv.get(v)
            if z is None or (dist.get(z,-1)==dist[u]+1 and dfs(z)):
                pu[u]=v; pv[v]=u; return True
        dist[u]=-1; return False
    while bfs():
        for u in left:
            if pu[u] is None: dfs(u)
    return tuple(sorted((u,v) for u,v in pu.items() if v is not None))

def infer_positive_budget_forcing(graph_a,graph_b,*,max_unmatched_total,max_common_edge_disagreements,max_forced_checks=2000):
    if max_unmatched_total<0 or max_common_edge_disagreements<0 or max_forced_checks<1: raise ValueError('bad budgets')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]: return PositiveBudgetCertificate('inconsistent_constraints',(),(),0,0,0,'attribute dimensions differ')
    n,m=len(a),len(b); k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m): return PositiveBudgetCertificate('inconsistent_constraints',(),(),k,0,0,'unmatched budget impossible')
    aa=defaultdict(list); bb=defaultdict(list)
    for i in range(n): aa[_key(x[i])].append(i)
    for j in range(m): bb[_key(y[j])].append(j)
    keys=set(aa)|set(bb); cap=sum(min(len(aa[q]),len(bb[q])) for q in keys)
    if cap<k:return PositiveBudgetCertificate('inconsistent_constraints',(),(),k,cap,0,'attribute inventory cannot reach minimum common nodes')
    anchors={}
    for q in keys:
        if len(aa[q])==1 and len(bb[q])==1 and cap-1<k: anchors[aa[q][0]]=bb[q][0]
    ap=tuple(sorted(anchors.items())); base=0
    for q in range(len(ap)):
        i,j=ap[q]
        for r in range(q):
            u,v=ap[r]; base += int(bool(a[i,u])!=bool(b[j,v]))
    if base>max_common_edge_disagreements:return PositiveBudgetCertificate('inconsistent_constraints',(),(),k,0,base,'forced anchors alone exceed edge budget')
    left=[i for i in range(n) if i not in anchors]; used=set(anchors.values()); right=[j for j in range(m) if j not in used]; need=max(0,k-len(anchors)); adj={i:[] for i in left}
    for i in left:
        for j in bb.get(_key(x[i]),()):
            if j in used: continue
            d=sum(int(bool(a[i,u])!=bool(b[j,v])) for u,v in ap)
            if base+d<=max_common_edge_disagreements: adj[i].append(j)
    match=_hk(adj,left,right); M=len(match)
    if M<need:return PositiveBudgetCertificate('inconsistent_constraints',(),(),k,M,base,'anchor-mismatch compatibility superset cannot reach minimum common nodes')
    extra=[]
    if M==need:
        if len(match)>max_forced_checks:return PositiveBudgetCertificate('undetermined_check_budget',(),(),k,M,base,'forced-edge recheck budget exceeded; no pairs released')
        for e in match:
            if len(_hk(adj,left,right,forbidden=e))<need: extra.append(e)
    forced=tuple(sorted(tuple(anchors.items())+tuple(extra))); witness=tuple(sorted(tuple(anchors.items())+match))
    if len(witness)<k or n+m-2*len(witness)>max_unmatched_total:return PositiveBudgetCertificate('undetermined_no_witness',(),(),k,M,base,'candidate witness misses unmatched budget')
    dis=0
    for q in range(len(witness)):
        i,j=witness[q]
        if not np.array_equal(x[i],y[j]):return PositiveBudgetCertificate('undetermined_no_witness',(),(),k,M,dis,'witness attribute mismatch')
        for r in range(q):
            u,v=witness[r]; dis += int(bool(a[i,u])!=bool(b[j,v]))
    if dis>max_common_edge_disagreements:return PositiveBudgetCertificate('undetermined_no_witness',(),(),k,M,dis,'candidate witness exceeds total edge budget; no pairs released')
    return PositiveBudgetCertificate('certified_forced_pairs' if forced else 'feasible_no_forced_pairs',forced,witness,k,M,dis,'non-anchor pairs are essential even in a superset candidate graph; witness directly verified')
