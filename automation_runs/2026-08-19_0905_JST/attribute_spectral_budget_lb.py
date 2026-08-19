from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from typing import Tuple
import math,numpy as np
from total_budget_assignment_lb import _minimum_cost_k_matching,_validate,_key,_disagreements

@dataclass(frozen=True)
class AttributeSpectralCertificate:
    status:str; forced_pairs:Tuple[Tuple[int,int],...]; witness_pairs:Tuple[Tuple[int,int],...]; minimum_common_nodes:int; anchor_assignment_lower_bound:int; spectral_internal_lower_bound:int; total_lower_bound:int; witness_disagreements:int; reason:str

def _ceil_safe(x:float)->int:return max(0,int(math.ceil(float(x)-1e-9)))

def attribute_block_spectral_lower_bound(a,b,x,y,left,right):
    ga,gb=defaultdict(list),defaultdict(list)
    for u in left:ga[_key(x[u])].append(u)
    for v in right:gb[_key(y[v])].append(v)
    if set(ga)!=set(gb):return None
    for q in ga:
        if len(ga[q])!=len(gb[q]):return None
    keys=sorted(ga.keys());total=0
    for q in keys:
        ia,ib=ga[q],gb[q]
        if len(ia)>1:
            la=np.linalg.eigvalsh(a[np.ix_(ia,ia)].astype(float));lb=np.linalg.eigvalsh(b[np.ix_(ib,ib)].astype(float));total+=_ceil_safe(0.5*np.sum((la-lb)**2))
    for ii,q in enumerate(keys):
        for r in keys[:ii]:
            sa=np.linalg.svd(a[np.ix_(ga[q],ga[r])].astype(float),compute_uv=False);sb=np.linalg.svd(b[np.ix_(gb[q],gb[r])].astype(float),compute_uv=False);total+=_ceil_safe(np.sum((sa-sb)**2))
    return int(total)

def infer_attribute_spectral_budget_forcing(graph_a,graph_b,*,max_unmatched_total:int,max_common_edge_disagreements:int,max_exclusion_checks:int=4000):
    if max_unmatched_total<0 or max_common_edge_disagreements<0 or max_exclusion_checks<1:raise ValueError('bad budgets')
    a,x=_validate(graph_a);b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:return AttributeSpectralCertificate('inconsistent_constraints',(),(),0,0,0,0,0,'attribute dimensions differ')
    n,m=len(a),len(b);k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m):return AttributeSpectralCertificate('inconsistent_constraints',(),(),k,0,0,0,0,'unmatched budget impossible')
    aa,bb=defaultdict(list),defaultdict(list)
    for i in range(n):aa[_key(x[i])].append(i)
    for j in range(m):bb[_key(y[j])].append(j)
    keys=set(aa)|set(bb);cap=sum(min(len(aa[q]),len(bb[q])) for q in keys)
    if cap<k:return AttributeSpectralCertificate('inconsistent_constraints',(),(),k,0,0,0,0,'attribute inventory cannot reach minimum common nodes')
    anchors={}
    for q in keys:
        if len(aa[q])==1 and len(bb[q])==1 and cap-1<k:anchors[aa[q][0]]=bb[q][0]
    ap=tuple(sorted(anchors.items()));base=_disagreements(a,b,ap)
    if base>max_common_edge_disagreements:return AttributeSpectralCertificate('inconsistent_constraints',(),(),k,0,0,base,base,'forced anchors alone exceed edge budget')
    left=[i for i in range(n) if i not in anchors];used=set(anchors.values());right=[j for j in range(m) if j not in used];need=max(0,k-len(anchors))
    if need!=len(left) or need!=len(right):return AttributeSpectralCertificate('undetermined_partial_selection',(),(),k,0,0,base,0,'spectral block bound currently requires full selection of remaining pools')
    cost={}
    for u in left:
        for v in bb.get(_key(x[u]),()):
            if v not in used:cost[(u,v)]=sum(int(bool(a[u,p])!=bool(b[v,q])) for p,q in ap)
    min_anchor,match=_minimum_cost_k_matching(left,right,cost,need)
    if min_anchor is None:return AttributeSpectralCertificate('inconsistent_constraints',(),(),k,0,0,base,0,'exact-attribute full matching impossible')
    spectral=attribute_block_spectral_lower_bound(a,b,x,y,left,right)
    if spectral is None:return AttributeSpectralCertificate('inconsistent_constraints',(),(),k,min_anchor,0,base+min_anchor,0,'attribute bucket inventories differ under required full remaining match')
    lb=base+min_anchor+spectral
    if lb>max_common_edge_disagreements:return AttributeSpectralCertificate('inconsistent_constraints',(),(),k,min_anchor,spectral,lb,0,'attribute-block spectral lower bound exceeds total edge budget')
    witness=tuple(sorted(ap+match));wd=_disagreements(a,b,witness)
    if wd>max_common_edge_disagreements:return AttributeSpectralCertificate('undetermined_no_witness',(),(),k,min_anchor,spectral,lb,wd,'lower-bound minimizer is not a directly feasible witness; no identities released')
    forced=list(ap)
    for z,e in enumerate(match):
        if z>=max_exclusion_checks:return AttributeSpectralCertificate('undetermined_check_budget',tuple(sorted(ap)),witness,k,min_anchor,spectral,lb,wd,'exclusion-check budget exceeded; only inventory anchors released')
        alt,_=_minimum_cost_k_matching(left,right,cost,need,forbidden=e)
        if alt is None or base+alt+spectral>max_common_edge_disagreements:forced.append(e)
    return AttributeSpectralCertificate('certified_forced_pairs' if forced else 'feasible_no_forced_pairs',tuple(sorted(forced)),witness,k,min_anchor,spectral,lb,wd,'forced pairs proven by inventory or exclusion after adding a permutation-invariant attribute-block spectral lower bound; witness directly verified')
