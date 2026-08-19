from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class ExactOrbitCertificate:
    status: str
    forced_pairs: Tuple[Tuple[int,int], ...]
    witness_count: int
    states_explored: int
    complete_enumeration: bool
    reason: str


def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)):
        raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)):
        raise ValueError('bad attributes')
    return a,x


def _key(row):
    return np.ascontiguousarray(row,dtype=np.float64).tobytes()


def exact_full_orbit_certificate(graph_a,graph_b,*,max_states=200000,max_witnesses=10000):
    """Bounded exact/full isomorphism-orbit certificate.

    All found mappings are directly constrained exact isomorphisms. The
    intersection of found mappings is an upper bound on the true forced-pair
    intersection. Therefore if that intersection becomes empty, `no forced
    pairs` is certified immediately even if enumeration is incomplete. If the
    search completes, the final intersection is the exact forced-pair set.
    State/witness limits otherwise cause fail-closed abstention.
    """
    if max_states<1 or max_witnesses<1:
        raise ValueError('limits must be positive')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if len(a)!=len(b) or x.shape[1]!=y.shape[1]:
        return ExactOrbitCertificate('inconsistent_constraints',(),0,0,True,'full exact isomorphism requires equal sizes and attribute dimensions')
    n=len(a); ax=[_key(r) for r in x]; by=[_key(r) for r in y]
    if Counter(ax)!=Counter(by) or Counter(map(int,a.sum(axis=1)))!=Counter(map(int,b.sum(axis=1))):
        return ExactOrbitCertificate('inconsistent_constraints',(),0,0,True,'attribute or degree inventories differ')

    domains={i:[j for j in range(n) if ax[i]==by[j] and int(a[i].sum())==int(b[j].sum())] for i in range(n)}
    if any(not d for d in domains.values()):
        return ExactOrbitCertificate('inconsistent_constraints',(),0,0,True,'empty exact-invariant domain')

    assign={}; used=set(); states=0; witnesses=0; intersection=None; limit_hit=False; certified_empty=False

    def compatible(i,j):
        for u,v in assign.items():
            if bool(a[i,u]) != bool(b[j,v]):
                return False
        return True

    def choose_next():
        best=None; best_options=None
        for i in range(n):
            if i in assign: continue
            options=[j for j in domains[i] if j not in used and compatible(i,j)]
            if best is None or len(options)<len(best_options):
                best=i; best_options=options
                if len(options)<=1: break
        return best,best_options

    def rec():
        nonlocal states,witnesses,intersection,limit_hit,certified_empty
        if certified_empty or limit_hit: return
        states += 1
        if states>max_states:
            limit_hit=True; return
        if len(assign)==n:
            p=np.asarray([assign[i] for i in range(n)],dtype=int)
            if not np.array_equal(x,y[p]) or not np.array_equal(a,b[np.ix_(p,p)]):
                return
            w=set(assign.items()); witnesses += 1
            intersection=set(w) if intersection is None else intersection & w
            if not intersection:
                certified_empty=True; return
            if witnesses>=max_witnesses:
                limit_hit=True
            return
        i,options=choose_next()
        if i is None or not options: return
        # Deterministic order; no arbitrary output identity is ever released
        # unless justified by the all-witness intersection rule.
        for j in options:
            assign[i]=j; used.add(j); rec(); used.remove(j); del assign[i]
            if certified_empty or limit_hit: return

    rec()
    if witnesses==0:
        if limit_hit:
            return ExactOrbitCertificate('undetermined_search_limit',(),0,states,False,'search limit reached before any exact isomorphism was certified')
        return ExactOrbitCertificate('inconsistent_constraints',(),0,states,True,'no exact isomorphism exists')
    if certified_empty:
        return ExactOrbitCertificate('certified_no_forced_pairs',(),witnesses,states,False,'intersection of directly verified isomorphism witnesses is empty')
    if limit_hit:
        return ExactOrbitCertificate('undetermined_search_limit',(),witnesses,states,False,'limits reached while nonempty witness intersection remained; no pairs released')
    return ExactOrbitCertificate('certified_exact_forced_pairs',tuple(sorted(intersection or ())),witnesses,states,True,'complete exact-isomorphism enumeration; forced set is witness intersection')
