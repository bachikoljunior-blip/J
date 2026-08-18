from __future__ import annotations
from dataclasses import dataclass
from typing import Dict,List,Sequence,Set,Tuple
import math,numpy as np
@dataclass(frozen=True)
class AlignmentConsensus:
    status:str; forced_pairs:Tuple[Tuple[int,int],...]; feasible_solutions:int; explored_states:int; minimum_common_nodes:int; reason:str
def _validate_graph(graph):
    a=(np.asarray(graph[0])!=0); x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)): raise ValueError("expected simple undirected adjacency")
    if x.ndim!=2 or x.shape[0]!=a.shape[0] or x.shape[1]<1 or not np.all(np.isfinite(x)): raise ValueError("bad attributes")
    return a,x
def _key(row): return np.ascontiguousarray(row,dtype=np.float64).tobytes()
def infer_partial_alignment_consensus(graph_a,graph_b,*,max_unmatched_total,max_common_edge_disagreements=0,max_states=200000,max_solutions=20000):
    if max_unmatched_total<0 or max_common_edge_disagreements<0: raise ValueError("edit budgets must be non-negative")
    if max_states<1 or max_solutions<1: raise ValueError("search budgets must be positive")
    a,x=_validate_graph(graph_a); b,y=_validate_graph(graph_b)
    if x.shape[1]!=y.shape[1]: return AlignmentConsensus("inconsistent_constraints",(),0,0,0,"attribute dimensions differ")
    n,m=a.shape[0],b.shape[0]; min_common=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if min_common>min(n,m): return AlignmentConsensus("inconsistent_constraints",(),0,0,min_common,"unmatched budget impossible")
    target_by_key:Dict[bytes,List[int]]={}
    for j in range(m): target_by_key.setdefault(_key(y[j]),[]).append(j)
    candidates=[list(target_by_key.get(_key(x[i]),[])) for i in range(n)]; order=sorted(range(n),key=lambda i:(len(candidates[i]),i)); mapping={}; used=np.zeros(m,dtype=bool); explored=0; solutions=[]; exhausted=False
    def inc_dis(i,j): return sum(bool(a[i,u])!=bool(b[j,v]) for u,v in mapping.items())
    def dfs(pos,dis):
        nonlocal explored,exhausted
        if exhausted:return
        explored+=1
        if explored>max_states: exhausted=True; return
        mapped=len(mapping); remaining=n-pos
        if mapped+remaining<min_common:return
        if pos==n:
            if mapped>=min_common and n+m-2*mapped<=max_unmatched_total and dis<=max_common_edge_disagreements:
                solutions.append(set(mapping.items()))
                if len(solutions)>max_solutions: exhausted=True
            return
        i=order[pos]
        for j in candidates[i]:
            if used[j]:continue
            inc=inc_dis(i,j)
            if dis+inc>max_common_edge_disagreements:continue
            mapping[i]=j; used[j]=True; dfs(pos+1,dis+inc); used[j]=False; del mapping[i]
            if exhausted:return
        if mapped+(remaining-1)>=min_common: dfs(pos+1,dis)
    dfs(0,0)
    if exhausted:return AlignmentConsensus("undetermined_budget_exhausted",(),len(solutions),explored,min_common,"enumeration incomplete; no pairs released")
    if not solutions:return AlignmentConsensus("inconsistent_constraints",(),0,explored,min_common,"no feasible alignment")
    forced=set(solutions[0])
    for s in solutions[1:]: forced&=s
    return AlignmentConsensus("unique_or_forced_consensus" if forced else "ambiguous_no_forced_pairs",tuple(sorted(forced)),len(solutions),explored,min_common,"only pairs shared by every feasible alignment are returned")
