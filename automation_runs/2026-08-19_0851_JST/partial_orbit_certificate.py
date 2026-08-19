from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class PartialOrbitCertificate:
    status: str
    forced_pairs: Tuple[Tuple[int,int], ...]
    witness_count: int
    states_explored: int
    minimum_common_nodes: int
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


def bounded_partial_orbit_certificate(
    graph_a,graph_b,*,max_unmatched_total,max_common_edge_disagreements,
    max_states=300000,max_witnesses=20000
):
    """Bounded exact-attribute partial-alignment forced/orbit certificate.

    It enumerates feasible mappings of the minimum required cardinality `k`.
    This suffices for forced-pair semantics: every larger feasible mapping has a
    size-k submapping that remains feasible, while any size-k mapping is already
    a valid alignment under the unmatched budget. Empty intersection over any
    found witness subset certifies no forced pair immediately. Nonempty forced
    sets are released only after complete enumeration.
    """
    if min(max_unmatched_total,max_common_edge_disagreements)<0 or max_states<1 or max_witnesses<1:
        raise ValueError('bad budgets or limits')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:
        return PartialOrbitCertificate('inconsistent_constraints',(),0,0,0,True,'attribute dimensions differ')
    n,m=len(a),len(b); k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m):
        return PartialOrbitCertificate('inconsistent_constraints',(),0,0,k,True,'unmatched budget impossible')
    ax=[_key(r) for r in x]; by=[_key(r) for r in y]
    domains={i:[j for j in range(m) if ax[i]==by[j]] for i in range(n)}

    assign={}; used=set(); skipped=set(); states=0; witnesses=0; intersection=None; limit_hit=False; certified_empty=False

    def choose_next():
        remaining=[i for i in range(n) if i not in assign and i not in skipped]
        if not remaining: return None,[]
        best=None; opts=None
        for i in remaining:
            o=[j for j in domains[i] if j not in used]
            if best is None or len(o)<len(opts):
                best=i; opts=o
                if len(o)==0: break
        return best,opts

    def incremental_disagreements(i,j):
        return sum(int(bool(a[i,u])!=bool(b[j,v])) for u,v in assign.items())

    def rec(current_dis):
        nonlocal states,witnesses,intersection,limit_hit,certified_empty
        if certified_empty or limit_hit: return
        states += 1
        if states>max_states:
            limit_hit=True; return
        need=k-len(assign)
        remaining=n-len(assign)-len(skipped)
        if need<0 or need>remaining or need>m-len(used): return
        if need==0:
            # Current mapping has exactly k pairs; all constraints have been
            # checked incrementally and attributes by domains.
            w=set(assign.items()); witnesses += 1
            intersection=set(w) if intersection is None else intersection & w
            if not intersection:
                certified_empty=True; return
            if witnesses>=max_witnesses: limit_hit=True
            return
        i,options=choose_next()
        if i is None: return
        for j in options:
            d=incremental_disagreements(i,j)
            if current_dis+d>max_common_edge_disagreements: continue
            assign[i]=j; used.add(j); rec(current_dis+d); used.remove(j); del assign[i]
            if certified_empty or limit_hit: return
        # Skipping i consumes unmatched budget implicitly; exact size k ensures
        # total unmatched count n+m-2k is within the declared budget.
        if remaining-1>=need:
            skipped.add(i); rec(current_dis); skipped.remove(i)

    rec(0)
    if witnesses==0:
        if limit_hit:
            return PartialOrbitCertificate('undetermined_search_limit',(),0,states,k,False,'search limit reached before a feasible size-k witness was certified')
        return PartialOrbitCertificate('inconsistent_constraints',(),0,states,k,True,'no feasible minimum-cardinality partial alignment exists')
    if certified_empty:
        return PartialOrbitCertificate('certified_no_forced_pairs',(),witnesses,states,k,False,'intersection of directly constrained feasible size-k witnesses is empty')
    if limit_hit:
        return PartialOrbitCertificate('undetermined_search_limit',(),witnesses,states,k,False,'limits reached while nonempty witness intersection remained; no pairs released')
    return PartialOrbitCertificate('certified_exact_forced_pairs',tuple(sorted(intersection or ())),witnesses,states,k,True,'complete feasible size-k enumeration; forced set is exact witness intersection')
