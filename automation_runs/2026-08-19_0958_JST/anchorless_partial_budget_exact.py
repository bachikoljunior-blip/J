from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations,permutations
import math,numpy as np
@dataclass(frozen=True)
class PartialBudgetSymmetryCertificate:
    status:str;forced_pairs:tuple[tuple[int,int],...];witness_pairs:tuple[tuple[int,int],...];feasible_mapping_count:int;minimum_common_nodes:int;explored_candidates:int;reason:str

def _validate(graph):
    a=np.asarray(graph[0],dtype=np.int8);x=np.asarray(graph[1]);
    if x.ndim==1:x=x[:,None]
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)) or not np.all((a==0)|(a==1)):raise ValueError('expected simple undirected graph')
    if x.ndim!=2 or len(x)!=len(a):raise ValueError('bad attributes')
    return a,x

def _dis(a,b,pairs):return sum(int(bool(a[i,u])!=bool(b[j,v])) for q,(i,j) in enumerate(pairs) for u,v in pairs[:q])
def infer_anchorless_partial_budget_forcing(graph_a,graph_b,*,max_unmatched_total:int,max_common_edge_disagreements:int,max_candidates:int=1_000_000):
    if max_unmatched_total<0 or max_common_edge_disagreements<0 or max_candidates<1:raise ValueError('bad budgets')
    a,x=_validate(graph_a);b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:return PartialBudgetSymmetryCertificate('inconsistent_constraints',(),(),0,0,0,'attribute dimensions differ')
    n,m=len(a),len(b);k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m):return PartialBudgetSymmetryCertificate('inconsistent_constraints',(),(),0,k,0,'unmatched budget impossible')
    feasible=[];explored=0
    for sa in combinations(range(n),k):
        for sb in combinations(range(m),k):
            for p in permutations(sb):
                explored+=1
                if explored>max_candidates:return PartialBudgetSymmetryCertificate('undetermined_search_budget',(),(),len(feasible),k,explored,'candidate cutoff reached; no identities released')
                pairs=tuple(zip(sa,p))
                if any(not np.array_equal(x[i],y[j]) for i,j in pairs):continue
                if _dis(a,b,pairs)<=max_common_edge_disagreements:feasible.append(pairs)
    if not feasible:return PartialBudgetSymmetryCertificate('inconsistent_constraints',(),(),0,k,explored,'no feasible minimum-cardinality partial mapping')
    common=set(feasible[0])
    for f in feasible[1:]:common.intersection_update(f)
    return PartialBudgetSymmetryCertificate('certified_forced_pairs' if common else 'feasible_no_forced_pairs',tuple(sorted(common)),tuple(sorted(feasible[0])),len(feasible),k,explored,'forced pairs are the intersection of every feasible minimum-cardinality budget-respecting partial map')
