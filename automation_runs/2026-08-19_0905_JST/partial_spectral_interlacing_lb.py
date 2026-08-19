from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from typing import Tuple
import math,numpy as np
from total_budget_assignment_lb import _minimum_cost_k_matching,_validate,_key,_disagreements

@dataclass(frozen=True)
class PartialSpectralCertificate:
    status:str; forced_pairs:Tuple[Tuple[int,int],...]; witness_pairs:Tuple[Tuple[int,int],...]; minimum_common_nodes:int; anchor_assignment_lower_bound:int; spectral_internal_lower_bound:int; total_lower_bound:int; witness_disagreements:int; reason:str

def _ceil_safe(x):return max(0,int(math.ceil(float(x)-1e-9)))

def induced_subgraph_spectral_interlacing_lower_bound(A,B,k):
    A=np.asarray(A,dtype=float);B=np.asarray(B,dtype=float)
    if A.ndim!=2 or B.ndim!=2 or A.shape[0]!=A.shape[1] or B.shape[0]!=B.shape[1]:raise ValueError('square matrices required')
    n,m=len(A),len(B)
    if k<0 or k>min(n,m):raise ValueError('bad k')
    if k<=1:return 0
    la=np.linalg.eigvalsh(A);lb=np.linalg.eigvalsh(B);s=0.0
    for i in range(k):
        alo,ahi=la[i],la[i+n-k];blo,bhi=lb[i],lb[i+m-k];gap=max(0.0,blo-ahi,alo-bhi);s+=gap*gap
    return _ceil_safe(0.5*s)

def infer_partial_spectral_budget_forcing(graph_a,graph_b,*,max_unmatched_total:int,max_common_edge_disagreements:int,max_exclusion_checks:int=4000):
    if max_unmatched_total<0 or max_common_edge_disagreements<0 or max_exclusion_checks<1:raise ValueError('bad budgets')
    a,x=_validate(graph_a);b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:return PartialSpectralCertificate('inconsistent_constraints',(),(),0,0,0,0,0,'attribute dimensions differ')
    n,m=len(a),len(b);k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m):return PartialSpectralCertificate('inconsistent_constraints',(),(),k,0,0,0,0,'unmatched budget impossible')
    aa,bb=defaultdict(list),defaultdict(list)
    for i in range(n):aa[_key(x[i])].append(i)
    for j in range(m):bb[_key(y[j])].append(j)
    keys=set(aa)|set(bb);cap=sum(min(len(aa[q]),len(bb[q])) for q in keys)
    if cap<k:return PartialSpectralCertificate('inconsistent_constraints',(),(),k,0,0,0,0,'attribute inventory cannot reach minimum common nodes')
    anchors={}
    for q in keys:
        if len(aa[q])==1 and len(bb[q])==1 and cap-1<k:anchors[aa[q][0]]=bb[q][0]
    ap=tuple(sorted(anchors.items()));base=_disagreements(a,b,ap)
    if base>max_common_edge_disagreements:return PartialSpectralCertificate('inconsistent_constraints',(),(),k,0,0,base,base,'forced anchors alone exceed edge budget')
    left=[i for i in range(n) if i not in anchors];used=set(anchors.values());right=[j for j in range(m) if j not in used];need=max(0,k-len(anchors));cost={}
    for u in left:
        for v in bb.get(_key(x[u]),()):
            if v not in used:cost[(u,v)]=sum(int(bool(a[u,p])!=bool(b[v,q])) for p,q in ap)
    min_anchor,match=_minimum_cost_k_matching(left,right,cost,need)
    if min_anchor is None:return PartialSpectralCertificate('inconsistent_constraints',(),(),k,0,0,base,0,'exact-attribute candidate graph cannot reach required cardinality')
    spectral=induced_subgraph_spectral_interlacing_lower_bound(a[np.ix_(left,left)],b[np.ix_(right,right)],need);lb=base+min_anchor+spectral
    if lb>max_common_edge_disagreements:return PartialSpectralCertificate('inconsistent_constraints',(),(),k,min_anchor,spectral,lb,0,'partial-selection spectral interlacing lower bound exceeds total edge budget')
    witness=tuple(sorted(ap+match));wd=_disagreements(a,b,witness)
    if wd>max_common_edge_disagreements:return PartialSpectralCertificate('undetermined_no_witness',(),(),k,min_anchor,spectral,lb,wd,'lower-bound minimizer is not a directly feasible witness; no identities released')
    forced=list(ap)
    for z,e in enumerate(match):
        if z>=max_exclusion_checks:return PartialSpectralCertificate('undetermined_check_budget',tuple(sorted(ap)),witness,k,min_anchor,spectral,lb,wd,'exclusion-check budget exceeded; only inventory anchors released')
        alt,_=_minimum_cost_k_matching(left,right,cost,need,forbidden=e)
        if alt is None or base+alt+spectral>max_common_edge_disagreements:forced.append(e)
    return PartialSpectralCertificate('certified_forced_pairs' if forced else 'feasible_no_forced_pairs',tuple(sorted(forced)),witness,k,min_anchor,spectral,lb,wd,'forced pairs proven by inventory or exclusion after adding a partial-selection spectral interlacing lower bound; witness directly verified')
