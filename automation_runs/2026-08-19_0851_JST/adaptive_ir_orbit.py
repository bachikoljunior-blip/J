from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class AdaptiveIROrbitCertificate:
    status: str
    forced_pairs: Tuple[Tuple[int,int], ...]
    witness_count: int
    states_explored: int
    maximum_depth: int
    complete_enumeration: bool
    reason: str


def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)):
        raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)):
        raise ValueError('bad attributes')
    return a,x


def _key(row): return np.ascontiguousarray(row,dtype=np.float64).tobytes()


def _compress_joint(sa,sb):
    lab={s:i for i,s in enumerate(sorted(set(sa+sb),key=repr))}
    return [lab[s] for s in sa],[lab[s] for s in sb]


def _refine(a,x,b,y,seeds,max_rounds):
    mark_a={u:t for t,(u,_) in enumerate(seeds)}; mark_b={v:t for t,(_,v) in enumerate(seeds)}
    sa=[(_key(x[i]),mark_a.get(i,-1)) for i in range(len(a))]
    sb=[(_key(y[j]),mark_b.get(j,-1)) for j in range(len(b))]
    ca,cb=_compress_joint(sa,sb)
    for _ in range(max_rounds):
        sa=[(ca[i],tuple(sorted(Counter(ca[k] for k in np.flatnonzero(a[i])).items()))) for i in range(len(a))]
        sb=[(cb[j],tuple(sorted(Counter(cb[k] for k in np.flatnonzero(b[j])).items()))) for j in range(len(b))]
        na,nb=_compress_joint(sa,sb)
        if na==ca and nb==cb: break
        ca,cb=na,nb
    return ca,cb


def exact_adaptive_ir_orbit(graph_a,graph_b,*,max_states=200000,max_witnesses=20000,max_rounds=64):
    """Resource-bounded complete exact isomorphism/orbit search via IR.

    At each node, joint 1-WL is run with all prior individualized source/target
    pairs uniquely marked. A non-singleton source color class is chosen, one
    source vertex is individualized, and every target vertex of the same color is
    branched. Any exact isomorphism follows exactly one branch. Discrete leaves
    induce one color-preserving candidate mapping, which is directly verified.

    Empty intersection of any verified witness subset certifies no forced pair
    immediately. Nonempty forced pairs are returned only when the entire search
    completes within the explicit resource limits.
    """
    if min(max_states,max_witnesses,max_rounds)<1: raise ValueError('limits must be positive')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if len(a)!=len(b) or x.shape[1]!=y.shape[1]:
        return AdaptiveIROrbitCertificate('inconsistent_constraints',(),0,0,0,True,'full exact alignment requires equal sizes and attribute dimensions')
    n=len(a); states=0; witnesses=0; max_depth_seen=0; inter=None; limit=False; empty=False

    def rec(seeds):
        nonlocal states,witnesses,max_depth_seen,inter,limit,empty
        if limit or empty: return
        states+=1; max_depth_seen=max(max_depth_seen,len(seeds))
        if states>max_states: limit=True; return
        ca,cb=_refine(a,x,b,y,seeds,max_rounds)
        if Counter(ca)!=Counter(cb): return
        counts=Counter(ca)
        if all(v==1 for v in counts.values()):
            pos={c:j for j,c in enumerate(cb)}; pairs=tuple((i,pos[ca[i]]) for i in range(n)); p=np.asarray([j for _,j in pairs],dtype=int)
            if not np.array_equal(x,y[p]) or not np.array_equal(a,b[np.ix_(p,p)]): return
            w=set(pairs); witnesses+=1; inter=set(w) if inter is None else inter&w
            if not inter: empty=True; return
            if witnesses>=max_witnesses: limit=True
            return
        # Smallest non-singleton color class minimizes branching.
        color=min((c for c,v in counts.items() if v>1),key=lambda c:(counts[c],c))
        src=[i for i,c in enumerate(ca) if c==color]; tgt=[j for j,c in enumerate(cb) if c==color]
        u=src[0]
        for v in tgt:
            rec(seeds+((u,v),))
            if limit or empty: return

    rec(())
    if witnesses==0:
        if limit:
            return AdaptiveIROrbitCertificate('undetermined_search_limit',(),0,states,max_depth_seen,False,'IR search limit reached before any exact isomorphism was certified')
        return AdaptiveIROrbitCertificate('inconsistent_constraints',(),0,states,max_depth_seen,True,'complete IR search found no exact isomorphism')
    if empty:
        return AdaptiveIROrbitCertificate('certified_no_forced_pairs',(),witnesses,states,max_depth_seen,False,'intersection of directly verified IR witnesses became empty')
    if limit:
        return AdaptiveIROrbitCertificate('undetermined_search_limit',(),witnesses,states,max_depth_seen,False,'IR limits reached while nonempty witness intersection remained; no identities released')
    return AdaptiveIROrbitCertificate('certified_exact_forced_pairs',tuple(sorted(inter or ())),witnesses,states,max_depth_seen,True,'complete resource-bounded IR enumeration; forced set is exact witness intersection')
