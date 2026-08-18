from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
from typing import Tuple
import numpy as np

@dataclass(frozen=True)
class WLAlignmentCertificate:
    status:str
    pairs:Tuple[Tuple[int,int],...]
    rounds:int
    reason:str

def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)): raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)): raise ValueError('bad attributes')
    return a,x

def _attr_key(row): return np.ascontiguousarray(row,dtype=np.float64).tobytes()

def _compress_joint(sa,sb):
    all_sigs=sa+sb; uniq={s:i for i,s in enumerate(sorted(set(all_sigs),key=repr))}
    return [uniq[s] for s in sa],[uniq[s] for s in sb]

def infer_full_alignment_wl(graph_a,graph_b,*,max_rounds=64):
    """Fail-closed scalable certifier for full exact attributed isomorphism.

    A mapping is released only when joint 1-WL refinement makes every color
    class singleton and the induced bijection passes direct adjacency and
    attribute verification. Non-singleton refinement classes cause abstention.
    """
    if max_rounds<1: raise ValueError('max_rounds must be positive')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if len(a)!=len(b) or x.shape[1]!=y.shape[1]:
        return WLAlignmentCertificate('inconsistent_constraints',(),0,'full exact alignment requires equal sizes and attribute dimensions')
    n=len(a); sa=[('attr',_attr_key(x[i])) for i in range(n)]; sb=[('attr',_attr_key(y[j])) for j in range(n)]; ca,cb=_compress_joint(sa,sb); rounds=0
    for r in range(max_rounds):
        sa=[]; sb=[]
        for i in range(n): sa.append((ca[i],tuple(sorted(Counter(ca[k] for k in np.flatnonzero(a[i])).items()))))
        for j in range(n): sb.append((cb[j],tuple(sorted(Counter(cb[k] for k in np.flatnonzero(b[j])).items()))))
        na,nb=_compress_joint(sa,sb); rounds=r+1
        if na==ca and nb==cb: break
        ca,cb=na,nb
    if Counter(ca)!=Counter(cb):
        return WLAlignmentCertificate('inconsistent_constraints',(),rounds,'WL color inventories differ')
    if any(v!=1 for v in Counter(ca).values()):
        return WLAlignmentCertificate('ambiguous_or_refinement_insufficient',(),rounds,'non-singleton WL class remains; no pairs released')
    pos_b={c:j for j,c in enumerate(cb)}; pairs=tuple((i,pos_b[c]) for i,c in enumerate(ca)); p=np.array([j for _,j in pairs],dtype=int)
    if not np.array_equal(x,y[p]) or not np.array_equal(a,b[np.ix_(p,p)]):
        return WLAlignmentCertificate('inconsistent_constraints',(),rounds,'induced singleton mapping failed direct verification')
    return WLAlignmentCertificate('certified_unique_alignment',pairs,rounds,'all WL classes singleton and induced bijection directly verified')
