from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from typing import Tuple
import math,numpy as np

from assignment_budget_lower_bound import budget_feasible_edge_superset
from essential_matching_scc import essential_edges_all_maximum_matchings

@dataclass(frozen=True)
class PositiveBudgetCertificate:
    status:str
    forced_pairs:Tuple[Tuple[int,int],...]
    witness_pairs:Tuple[Tuple[int,int],...]
    minimum_common_nodes:int
    candidate_matching_size:int
    edge_disagreements:int
    reason:str
    assignment_anchor_lower_bound:int=0
    candidate_edge_count:int=0


def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)):
        raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)):
        raise ValueError('bad attributes')
    return a,x


def _key(row):
    return np.ascontiguousarray(row,dtype=np.float64).tobytes()


def _direct_disagreements(a,b,witness):
    dis=0
    for q in range(len(witness)):
        i,j=witness[q]
        for r in range(q):
            u,v=witness[r]
            dis += int(bool(a[i,u])!=bool(b[j,v]))
    return dis


def infer_positive_budget_forcing(graph_a,graph_b,*,max_unmatched_total,max_common_edge_disagreements,max_forced_checks=2000):
    # max_forced_checks is retained for API compatibility; SCC extraction no longer
    # performs one matching recomputation per candidate edge.
    if max_unmatched_total<0 or max_common_edge_disagreements<0 or max_forced_checks<1:
        raise ValueError('bad budgets')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:
        return PositiveBudgetCertificate('inconsistent_constraints',(),(),0,0,0,'attribute dimensions differ')
    n,m=len(a),len(b); k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m):
        return PositiveBudgetCertificate('inconsistent_constraints',(),(),k,0,0,'unmatched budget impossible')

    aa=defaultdict(list); bb=defaultdict(list)
    for i in range(n): aa[_key(x[i])].append(i)
    for j in range(m): bb[_key(y[j])].append(j)
    keys=set(aa)|set(bb)
    cap=sum(min(len(aa[q]),len(bb[q])) for q in keys)
    if cap<k:
        return PositiveBudgetCertificate('inconsistent_constraints',(),(),k,cap,0,'attribute inventory cannot reach minimum common nodes')

    # Capacity-critical exact-attribute singleton pairs are forced anchors.
    anchors={}
    for q in keys:
        if len(aa[q])==1 and len(bb[q])==1 and cap-1<k:
            anchors[aa[q][0]]=bb[q][0]
    ap=tuple(sorted(anchors.items()))
    base=_direct_disagreements(a,b,ap)
    if base>max_common_edge_disagreements:
        return PositiveBudgetCertificate('inconsistent_constraints',(),(),k,0,base,'forced anchors alone exceed edge budget')

    left=[i for i in range(n) if i not in anchors]
    used=set(anchors.values())
    right=[j for j in range(m) if j not in used]
    need=max(0,k-len(anchors))

    # Each remaining assignment edge receives its exact disagreement count to
    # already-forced anchors. Summing these edge costs over a matching counts
    # every remaining-to-anchor disagreement exactly once. Disagreements among
    # remaining pairs are omitted, therefore min-cost assignment is a sound
    # lower bound on total common-edge disagreement.
    costs={}
    for i in left:
        for j in bb.get(_key(x[i]),()):
            if j in used:
                continue
            costs[(i,j)]=sum(
                int(bool(a[i,u])!=bool(b[j,v])) for u,v in ap
            )

    remaining_budget=max_common_edge_disagreements-base
    kept,lb=budget_feasible_edge_superset(costs,left,right,need,remaining_budget)
    if not lb.feasible or lb.minimum_cost>remaining_budget:
        lower=0 if not lb.feasible else int(lb.minimum_cost)
        return PositiveBudgetCertificate(
            'inconsistent_constraints',(),(),k,0,base,
            'minimum total anchor-disagreement assignment lower bound exceeds remaining edge budget',
            lower,0
        )

    adj={i:[] for i in left}
    for i,j in kept:
        adj[i].append(j)
    em=essential_edges_all_maximum_matchings(adj,left,right)
    M=em.maximum_size
    if M<need:
        return PositiveBudgetCertificate(
            'inconsistent_constraints',(),(),k,M,base,
            'assignment-budget compatibility superset cannot reach minimum common nodes',
            int(lb.minimum_cost),len(kept)
        )

    # Only when maximum cardinality equals the required cardinality are edges
    # essential across all maximum matchings also essential across every
    # cardinality-need candidate assignment.
    extra=em.essential_edges if M==need else ()
    forced=tuple(sorted(tuple(anchors.items())+tuple(extra)))

    # Use the min-cost lower-bound witness. It is only a candidate because the
    # assignment objective omits pairwise disagreements among remaining nodes.
    witness=tuple(sorted(tuple(anchors.items())+tuple(lb.matching)))
    if len(witness)<k or n+m-2*len(witness)>max_unmatched_total:
        return PositiveBudgetCertificate(
            'undetermined_no_witness',(),(),k,M,base,
            'candidate witness misses unmatched budget',int(lb.minimum_cost),len(kept)
        )
    for i,j in witness:
        if not np.array_equal(x[i],y[j]):
            return PositiveBudgetCertificate(
                'undetermined_no_witness',(),(),k,M,base,
                'witness attribute mismatch',int(lb.minimum_cost),len(kept)
            )
    dis=_direct_disagreements(a,b,witness)
    if dis>max_common_edge_disagreements:
        return PositiveBudgetCertificate(
            'undetermined_no_witness',(),(),k,M,dis,
            'minimum-anchor-cost witness exceeds full total edge budget; no pairs released',
            int(lb.minimum_cost),len(kept)
        )

    return PositiveBudgetCertificate(
        'certified_forced_pairs' if forced else 'feasible_no_forced_pairs',
        forced,witness,k,M,dis,
        'forced pairs are essential in a total-anchor-budget-feasible assignment superset; witness directly verified',
        int(lb.minimum_cost),len(kept)
    )
