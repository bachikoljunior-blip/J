from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple
import numpy as np

from assignment_budget_lower_bound import budget_feasible_edge_superset
from essential_matching_scc import essential_edges_all_maximum_matchings


@dataclass(frozen=True)
class AnchorlessPartialCertificate:
    status: str
    forced_pairs: Tuple[Tuple[int,int], ...]
    witness_pairs: Tuple[Tuple[int,int], ...]
    minimum_common_nodes: int
    histogram_assignment_lower_bound: int
    implied_edge_disagreement_lower_bound: int
    candidate_matching_size: int
    candidate_edge_count: int
    witness_edge_disagreements: int
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


def _neighbor_histograms(a,x,keys):
    pos={q:t for t,q in enumerate(keys)}
    row_keys=[_key(r) for r in x]
    h=np.zeros((len(a),len(keys)),dtype=int)
    for i in range(len(a)):
        for v in np.flatnonzero(a[i]):
            h[i,pos[row_keys[v]]] += 1
    return h,row_keys


def _direct_disagreements(a,b,witness):
    d=0
    for q,(i,j) in enumerate(witness):
        for u,v in witness[:q]:
            d += int(bool(a[i,u]) != bool(b[j,v]))
    return d


def _edge_lb(hist_cost,k,max_unmatched_total):
    # Let S be the sum of L1 attribute-neighborhood histogram differences over
    # k matched vertices. Each unmatched vertex can affect at most k incident
    # histogram counts, so all unmatched vertices account for at most k*U of S.
    # Each disagreement between two matched vertices affects at most two endpoint
    # histogram counts. Therefore S <= k*U + 2*E for every feasible alignment.
    residual=max(0,hist_cost-k*max_unmatched_total)
    return (residual+1)//2


def infer_anchorless_partial_global_lb(
    graph_a,graph_b,*,max_unmatched_total,max_common_edge_disagreements
):
    """Sound-but-incomplete anchorless partial-edit forced-pair certificate.

    Exact persistent attributes are required. No pre-existing identity anchors are
    used. Global min-cost cardinality assignment over attribute-neighborhood
    histograms supplies a lower bound; infeasible candidate edges are removed.
    Essential edges are released only when candidate maximum cardinality equals
    the required common cardinality and a full witness passes direct checking.
    """
    if max_unmatched_total<0 or max_common_edge_disagreements<0:
        raise ValueError('budgets must be non-negative')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:
        return AnchorlessPartialCertificate('inconsistent_constraints',(),(),0,0,0,0,0,0,'attribute dimensions differ')
    n,m=len(a),len(b)
    k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m):
        return AnchorlessPartialCertificate('inconsistent_constraints',(),(),k,0,0,0,0,0,'unmatched budget impossible')

    keys=sorted(set(_key(r) for r in x)|set(_key(r) for r in y))
    ha,ka=_neighbor_histograms(a,x,keys); hb,kb=_neighbor_histograms(b,y,keys)
    costs={}
    for i in range(n):
        for j in range(m):
            if ka[i]==kb[j]:
                costs[(i,j)]=int(np.abs(ha[i]-hb[j]).sum())

    # A histogram-cost sum S is compatible with edge budget E only if
    # S <= k*U + 2*E. Use this as the min-cost assignment budget.
    hist_budget=k*max_unmatched_total + 2*max_common_edge_disagreements
    kept,lb=budget_feasible_edge_superset(costs,range(n),range(m),k,hist_budget)
    if not lb.feasible:
        return AnchorlessPartialCertificate('inconsistent_constraints',(),(),k,0,0,0,0,0,'exact-attribute assignment cannot reach minimum common cardinality')
    edge_lb=_edge_lb(int(lb.minimum_cost),k,max_unmatched_total)
    if edge_lb>max_common_edge_disagreements:
        return AnchorlessPartialCertificate('inconsistent_constraints',(),(),k,int(lb.minimum_cost),edge_lb,0,0,0,'global histogram assignment lower bound exceeds edge-disagreement budget')

    adj={i:[] for i in range(n)}
    for i,j in kept:
        adj[i].append(j)
    em=essential_edges_all_maximum_matchings(adj,range(n),range(m))
    if em.maximum_size<k:
        return AnchorlessPartialCertificate('inconsistent_constraints',(),(),k,int(lb.minimum_cost),edge_lb,em.maximum_size,len(kept),0,'global-lower-bound candidate superset cannot reach required cardinality')

    forced=em.essential_edges if em.maximum_size==k else ()
    witness=tuple(sorted(lb.matching))
    if len(witness)!=k or n+m-2*k>max_unmatched_total:
        return AnchorlessPartialCertificate('undetermined_no_witness',(),(),k,int(lb.minimum_cost),edge_lb,em.maximum_size,len(kept),0,'lower-bound witness has wrong cardinality')
    for i,j in witness:
        if not np.array_equal(x[i],y[j]):
            return AnchorlessPartialCertificate('undetermined_no_witness',(),(),k,int(lb.minimum_cost),edge_lb,em.maximum_size,len(kept),0,'witness attribute mismatch')
    dis=_direct_disagreements(a,b,witness)
    if dis>max_common_edge_disagreements:
        return AnchorlessPartialCertificate('undetermined_no_witness',(),(),k,int(lb.minimum_cost),edge_lb,em.maximum_size,len(kept),dis,'minimum-histogram witness fails full edge budget; no identities released')

    return AnchorlessPartialCertificate(
        'certified_forced_pairs' if forced else 'feasible_no_forced_pairs',
        tuple(sorted(forced)),witness,k,int(lb.minimum_cost),edge_lb,
        em.maximum_size,len(kept),dis,
        'forced pairs are essential in a global histogram-budget superset and witness is directly verified'
    )
