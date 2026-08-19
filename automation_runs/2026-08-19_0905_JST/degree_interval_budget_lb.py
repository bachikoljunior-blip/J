from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
from collections import defaultdict
import math
import numpy as np
from total_budget_assignment_lb import _minimum_cost_k_matching,_validate,_key,_disagreements

@dataclass(frozen=True)
class DegreeIntervalCertificate:
    status:str; forced_pairs:Tuple[Tuple[int,int],...]; witness_pairs:Tuple[Tuple[int,int],...]; minimum_common_nodes:int; lower_bound_disagreements:int; witness_disagreements:int; reason:str

def _interval_gap(lo1,hi1,lo2,hi2):
    if hi1<lo2:return lo2-hi1
    if hi2<lo1:return lo1-hi2
    return 0

def _selected_degree_interval(adj,node,pool,need):
    if need<=0:return (0,0)
    deg=sum(int(bool(adj[node,u])) for u in pool if u!=node); omitted=len(pool)-need
    return int(max(0,deg-omitted)),int(min(deg,need-1))

def infer_degree_interval_budget_forcing(graph_a,graph_b,*,max_unmatched_total:int,max_common_edge_disagreements:int,max_exclusion_checks:int=4000):
    if max_unmatched_total<0 or max_common_edge_disagreements<0 or max_exclusion_checks<1:raise ValueError('bad budgets')
    a,x=_validate(graph_a);b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:return DegreeIntervalCertificate('inconsistent_constraints',(),(),0,0,0,'attribute dimensions differ')
    n,m=len(a),len(b);k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m):return DegreeIntervalCertificate('inconsistent_constraints',(),(),k,0,0,'unmatched budget impossible')
    aa,bb=defaultdict(list),defaultdict(list)
    for i in range(n):aa[_key(x[i])].append(i)
    for j in range(m):bb[_key(y[j])].append(j)
    keys=set(aa)|set(bb);cap=sum(min(len(aa[q]),len(bb[q])) for q in keys)
    if cap<k:return DegreeIntervalCertificate('inconsistent_constraints',(),(),k,0,0,'attribute inventory cannot reach minimum common nodes')
    anchors={}
    for q in keys:
        if len(aa[q])==1 and len(bb[q])==1 and cap-1<k:anchors[aa[q][0]]=bb[q][0]
    ap=tuple(sorted(anchors.items()));base=_disagreements(a,b,ap)
    if base>max_common_edge_disagreements:return DegreeIntervalCertificate('inconsistent_constraints',(),(),k,base,base,'forced anchors alone exceed edge budget')
    left=[i for i in range(n) if i not in anchors];used=set(anchors.values());right=[j for j in range(m) if j not in used];need=max(0,k-len(anchors))
    ia={u:_selected_degree_interval(a,u,left,need) for u in left};ib={v:_selected_degree_interval(b,v,right,need) for v in right};scaled={}
    for u in left:
        for v in bb.get(_key(x[u]),()):
            if v in used:continue
            anchor=sum(int(bool(a[u,p])!=bool(b[v,q])) for p,q in ap);gap=_interval_gap(*ia[u],*ib[v]);scaled[(u,v)]=int(2*anchor+gap)
    min_scaled,match=_minimum_cost_k_matching(left,right,scaled,need)
    if min_scaled is None:return DegreeIntervalCertificate('inconsistent_constraints',(),(),k,0,0,'candidate graph cannot reach minimum common nodes')
    lb=base+math.ceil(min_scaled/2)
    if lb>max_common_edge_disagreements:return DegreeIntervalCertificate('inconsistent_constraints',(),(),k,lb,0,'degree-interval assignment lower bound exceeds total edge budget')
    witness=tuple(sorted(ap+match));wd=_disagreements(a,b,witness)
    if len(witness)<k or n+m-2*len(witness)>max_unmatched_total or wd>max_common_edge_disagreements:return DegreeIntervalCertificate('undetermined_no_witness',(),(),k,lb,wd,'lower-bound minimizer is not a directly feasible full witness; no identities released')
    forced=list(ap);checks=0
    for e in match:
        if checks>=max_exclusion_checks:return DegreeIntervalCertificate('undetermined_check_budget',tuple(sorted(ap)),witness,k,lb,wd,'exclusion-check budget exceeded; only inventory anchors released')
        checks+=1;alt,_=_minimum_cost_k_matching(left,right,scaled,need,forbidden=e)
        if alt is None or base+math.ceil(alt/2)>max_common_edge_disagreements:forced.append(e)
    return DegreeIntervalCertificate('certified_forced_pairs' if forced else 'feasible_no_forced_pairs',tuple(sorted(forced)),witness,k,lb,wd,'forced pairs proven by inventory or exclusion under a global anchor-plus-degree-interval lower bound; witness directly verified')
