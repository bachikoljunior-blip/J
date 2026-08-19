from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class WL2AlignmentCertificate:
    status: str
    pairs: Tuple[Tuple[int, int], ...]
    rounds: int
    reason: str


def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)):
        raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)):
        raise ValueError('bad attributes')
    return a,x


def _attr_key(row):
    return np.ascontiguousarray(row,dtype=np.float64).tobytes()


def _compress_joint(sig_a,sig_b):
    all_sigs=sig_a+sig_b
    labels={s:i for i,s in enumerate(sorted(set(all_sigs),key=repr))}
    return [labels[s] for s in sig_a],[labels[s] for s in sig_b]


def _initial_pair_colors(a,x,b,y):
    na=len(a); nb=len(b); sa=[]; sb=[]
    for i in range(na):
        for j in range(na):
            sa.append((_attr_key(x[i]),_attr_key(x[j]),i==j,bool(a[i,j])))
    for i in range(nb):
        for j in range(nb):
            sb.append((_attr_key(y[i]),_attr_key(y[j]),i==j,bool(b[i,j])))
    ca,cb=_compress_joint(sa,sb)
    return np.asarray(ca,dtype=int).reshape(na,na),np.asarray(cb,dtype=int).reshape(nb,nb)


def infer_full_alignment_2wl(graph_a,graph_b,*,max_rounds=32):
    """Fail-closed exact/full alignment certifier using joint 2-WL refinement.

    This is a higher-order fallback for anchorless duplicate-attribute graphs.
    A mapping is released only when diagonal pair-colors become singleton on both
    graphs, the color inventories agree, and the induced bijection is directly
    verified against every attribute and adjacency entry.
    """
    if max_rounds<1:
        raise ValueError('max_rounds must be positive')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if len(a)!=len(b) or x.shape[1]!=y.shape[1]:
        return WL2AlignmentCertificate('inconsistent_constraints',(),0,'full exact alignment requires equal sizes and attribute dimensions')
    n=len(a)
    ca,cb=_initial_pair_colors(a,x,b,y); rounds=0
    for r in range(max_rounds):
        sa=[]; sb=[]
        for i in range(n):
            for j in range(n):
                # Standard 2-WL update: retain current ordered-pair color and
                # aggregate all two-step color pairs through an intermediate k.
                sa.append((int(ca[i,j]),tuple(sorted(Counter((int(ca[i,k]),int(ca[k,j])) for k in range(n)).items()))))
                sb.append((int(cb[i,j]),tuple(sorted(Counter((int(cb[i,k]),int(cb[k,j])) for k in range(n)).items()))))
        na,nb=_compress_joint(sa,sb)
        na=np.asarray(na,dtype=int).reshape(n,n); nb=np.asarray(nb,dtype=int).reshape(n,n)
        rounds=r+1
        if np.array_equal(na,ca) and np.array_equal(nb,cb):
            break
        ca,cb=na,nb

    da=[int(ca[i,i]) for i in range(n)]; db=[int(cb[j,j]) for j in range(n)]
    if Counter(da)!=Counter(db):
        return WL2AlignmentCertificate('inconsistent_constraints',(),rounds,'2-WL diagonal color inventories differ')
    if any(v!=1 for v in Counter(da).values()):
        return WL2AlignmentCertificate('ambiguous_or_refinement_insufficient',(),rounds,'non-singleton 2-WL diagonal class remains; no pairs released')
    pos_b={c:j for j,c in enumerate(db)}
    pairs=tuple((i,pos_b[da[i]]) for i in range(n)); p=np.asarray([j for _,j in pairs],dtype=int)
    if not np.array_equal(x,y[p]) or not np.array_equal(a,b[np.ix_(p,p)]):
        return WL2AlignmentCertificate('inconsistent_constraints',(),rounds,'2-WL singleton mapping failed direct verification')
    return WL2AlignmentCertificate('certified_unique_alignment',pairs,rounds,'all 2-WL diagonal classes singleton and induced bijection directly verified')
