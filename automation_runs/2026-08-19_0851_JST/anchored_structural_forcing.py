from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from typing import Tuple
import math,numpy as np

@dataclass(frozen=True)
class AnchoredStructuralCertificate:
    status:str; forced_pairs:Tuple[Tuple[int,int],...]; rounds:int; minimum_common_nodes:int; reason:str

def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)): raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)): raise ValueError('bad attributes')
    return a,x

def _key(row): return np.ascontiguousarray(row,dtype=np.float64).tobytes()

def infer_anchored_zero_edge_forcing(graph_a,graph_b,*,max_unmatched_total,max_common_edge_disagreements=0,max_rounds=256):
    if max_common_edge_disagreements!=0: return AnchoredStructuralCertificate('unsupported_positive_edge_budget',(),0,0,'sound propagation currently requires zero common-edge disagreements')
    if max_unmatched_total<0 or max_rounds<1: raise ValueError('bad budgets')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]: return AnchoredStructuralCertificate('inconsistent_constraints',(),0,0,'attribute dimensions differ')
    n,m=len(a),len(b); k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m): return AnchoredStructuralCertificate('inconsistent_constraints',(),0,k,'unmatched budget impossible')
    aa=defaultdict(list); bb=defaultdict(list)
    for i in range(n): aa[_key(x[i])].append(i)
    for j in range(m): bb[_key(y[j])].append(j)
    keys=set(aa)|set(bb); cap=sum(min(len(aa[q]),len(bb[q])) for q in keys)
    if cap<k: return AnchoredStructuralCertificate('inconsistent_constraints',(),0,k,'attribute inventory cannot reach minimum common nodes')
    forced={}
    for q in keys:
        if len(aa[q])==1 and len(bb[q])==1 and cap-1<k: forced[aa[q][0]]=bb[q][0]
    rounds=0
    for rr in range(max_rounds):
        rounds=rr+1; anchors=tuple(sorted(forced.items())); used_b=set(forced.values()); need=max(0,k-len(forced)); ba=defaultdict(list); bc=defaultdict(list)
        for i in range(n):
            if i not in forced: ba[(_key(x[i]),tuple(int(a[i,u]) for u,_ in anchors))].append(i)
        for j in range(m):
            if j not in used_b: bc[(_key(y[j]),tuple(int(b[j,v]) for _,v in anchors))].append(j)
        sigs=set(ba)|set(bc); remcap=sum(min(len(ba[q]),len(bc[q])) for q in sigs)
        if remcap<need: return AnchoredStructuralCertificate('inconsistent_constraints',(),rounds,k,'anchor-conditioned inventory cannot reach minimum common nodes')
        add=[]
        for q in sigs:
            if len(ba[q])==1 and len(bc[q])==1 and remcap-1<need: add.append((ba[q][0],bc[q][0]))
        if not add: break
        for i,j in add: forced[i]=j
    # Existence witness: complete remaining refined buckets deterministically and verify exact common edges.
    anchors=tuple(sorted(forced.items())); used_b=set(forced.values()); pairs=list(anchors); ba=defaultdict(list); bc=defaultdict(list)
    for i in range(n):
        if i not in forced: ba[(_key(x[i]),tuple(int(a[i,u]) for u,_ in anchors))].append(i)
    for j in range(m):
        if j not in used_b: bc[(_key(y[j]),tuple(int(b[j,v]) for _,v in anchors))].append(j)
    for q in sorted(set(ba)|set(bc),key=repr):
        la=sorted(ba[q]); lb=sorted(bc[q]); z=min(len(la),len(lb)); pairs.extend(zip(la[:z],lb[:z]))
    if len(pairs)<k or n+m-2*len(pairs)>max_unmatched_total: return AnchoredStructuralCertificate('undetermined_no_witness',(),rounds,k,'no simple feasible witness; no pairs released')
    for q in range(len(pairs)):
        i,j=pairs[q]
        if not np.array_equal(x[i],y[j]): return AnchoredStructuralCertificate('undetermined_no_witness',(),rounds,k,'witness attribute mismatch')
        for r in range(q):
            u,v=pairs[r]
            if bool(a[i,u])!=bool(b[j,v]): return AnchoredStructuralCertificate('undetermined_no_witness',(),rounds,k,'witness edge mismatch; no pairs released')
    out=tuple(sorted(forced.items()))
    return AnchoredStructuralCertificate('certified_structural_forced_pairs' if out else 'feasible_no_forced_pairs',out,rounds,k,'forced by iterative adjacency-to-forced-anchor capacity with verified feasible witness')
