from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict,Counter
from typing import Tuple
import math,numpy as np

@dataclass(frozen=True)
class PartialForcedCertificate:
    status:str; forced_pairs:Tuple[Tuple[int,int],...]; witness_pairs:Tuple[Tuple[int,int],...]; minimum_common_nodes:int; attribute_capacity:int; edge_disagreements:int; reason:str

def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)): raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)): raise ValueError('bad attributes')
    return a,x

def _key(row): return np.ascontiguousarray(row,dtype=np.float64).tobytes()
def _node_signature(a,x,i):
    hist=Counter(_key(x[j]) for j in np.flatnonzero(a[i])); return (int(a[i].sum()),tuple(sorted(hist.items())))

def infer_attribute_capacity_forced(graph_a,graph_b,*,max_unmatched_total,max_common_edge_disagreements=0):
    if max_unmatched_total<0 or max_common_edge_disagreements<0: raise ValueError('budgets must be non-negative')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]: return PartialForcedCertificate('inconsistent_constraints',(),(),0,0,0,'attribute dimensions differ')
    n,m=len(a),len(b); k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m): return PartialForcedCertificate('inconsistent_constraints',(),(),k,0,0,'unmatched budget impossible')
    aa=defaultdict(list); bb=defaultdict(list)
    for i in range(n): aa[_key(x[i])].append(i)
    for j in range(m): bb[_key(y[j])].append(j)
    keys=set(aa)|set(bb); cap=sum(min(len(aa[q]),len(bb[q])) for q in keys)
    if cap<k: return PartialForcedCertificate('inconsistent_constraints',(),(),k,cap,0,'exact-attribute inventory cannot supply minimum common nodes')
    forced=[]
    for q in keys:
        if len(aa[q])==1 and len(bb[q])==1 and cap-1<k: forced.append((aa[q][0],bb[q][0]))
    forced=tuple(sorted(forced))
    witness=[]
    for q in sorted(keys,key=repr):
        la=sorted(aa[q],key=lambda i:(_node_signature(a,x,i),i)); lb=sorted(bb[q],key=lambda j:(_node_signature(b,y,j),j)); z=min(len(la),len(lb)); witness.extend(zip(la[:z],lb[:z]))
    witness=tuple(sorted(witness))
    if len(witness)<k or n+m-2*len(witness)>max_unmatched_total: return PartialForcedCertificate('undetermined_no_witness',(),(),k,cap,0,'capacity sufficient but witness construction failed')
    dis=0
    for q in range(len(witness)):
        i,j=witness[q]
        for r in range(q):
            u,v=witness[r]; dis+=int(bool(a[i,u])!=bool(b[j,v]))
    if dis>max_common_edge_disagreements: return PartialForcedCertificate('undetermined_no_witness',(),(),k,cap,dis,'candidate witness exceeds edge budget; no identity pairs released')
    return PartialForcedCertificate('certified_attribute_forced_pairs' if forced else 'feasible_no_attribute_forced_pairs',forced,witness,k,cap,dis,'pairs are forced by exact-attribute capacity and a feasible witness was directly verified')
