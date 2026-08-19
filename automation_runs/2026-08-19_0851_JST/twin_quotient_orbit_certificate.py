from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class TwinQuotientCertificate:
    status: str
    forced_pairs: Tuple[Tuple[int,int], ...]
    source_modules: int
    target_modules: int
    quotient_witnesses: int
    quotient_states: int
    complete_quotient_enumeration: bool
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


def _twin_partition(a,x):
    n=len(a); parent=list(range(n)); attrs=[_key(r) for r in x]
    def find(z):
        while parent[z]!=z:
            parent[z]=parent[parent[z]]; z=parent[z]
        return z
    def union(u,v):
        ru,rv=find(u),find(v)
        if ru!=rv: parent[rv]=ru
    for u in range(n):
        for v in range(u+1,n):
            if attrs[u]!=attrs[v]: continue
            if all(bool(a[u,w])==bool(a[v,w]) for w in range(n) if w!=u and w!=v):
                union(u,v)
    groups={}
    for i in range(n): groups.setdefault(find(i),[]).append(i)
    out=[]
    for members in groups.values():
        members=tuple(sorted(members))
        if len(members)>1:
            aset={attrs[i] for i in members}
            outside=[w for w in range(n) if w not in members]
            module_ok=len(aset)==1 and all(len({bool(a[i,w]) for i in members})==1 for w in outside)
            internal={bool(a[u,v]) for z,u in enumerate(members) for v in members[z+1:]}
            module_ok=module_ok and len(internal)<=1
            if not module_ok:
                out.extend((i,) for i in members); continue
        out.append(members)
    return tuple(sorted(out,key=lambda g:g[0]))


def _quotient(a,x,parts):
    q=len(parts); qa=np.zeros((q,q),dtype=bool); meta=[]
    for z,g in enumerate(parts):
        internal=False if len(g)<2 else bool(a[g[0],g[1]])
        meta.append((_key(x[g[0]]),len(g),internal))
    for i in range(q):
        for j in range(i+1,q):
            e=bool(a[parts[i][0],parts[j][0]])
            qa[i,j]=qa[j,i]=e
            # verified module property guarantees representative edge is uniform
    return qa,tuple(meta)


def twin_quotient_orbit_certificate(graph_a,graph_b,*,max_quotient_states=100000,max_quotient_witnesses=10000):
    """Exact/full orbit certificate using verified true/false-twin modules.

    Arbitrary permutations within a verified non-singleton twin module are exact
    automorphisms. Quotient isomorphisms are enumerated on the compressed graph.
    Original forced identities can therefore arise only from quotient pairs that
    are forced and whose source and target modules are both singletons.
    """
    if max_quotient_states<1 or max_quotient_witnesses<1:
        raise ValueError('limits must be positive')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if len(a)!=len(b) or x.shape[1]!=y.shape[1]:
        return TwinQuotientCertificate('inconsistent_constraints',(),0,0,0,0,True,'full exact alignment requires equal sizes and attribute dimensions')
    pa=_twin_partition(a,x); pb=_twin_partition(b,y)
    qa,ma=_quotient(a,x,pa); qb,mb=_quotient(b,y,pb)
    if len(pa)!=len(pb):
        return TwinQuotientCertificate('inconsistent_constraints',(),len(pa),len(pb),0,0,True,'twin quotient sizes differ')
    q=len(pa)
    domains={i:[j for j in range(q) if ma[i]==mb[j] and int(qa[i].sum())==int(qb[j].sum())] for i in range(q)}
    if any(not d for d in domains.values()):
        return TwinQuotientCertificate('inconsistent_constraints',(),q,q,0,0,True,'empty quotient invariant domain')

    assign={}; used=set(); states=0; witnesses=0; intersection=None; limit=False; no_original_forced=False

    def compatible(i,j):
        return all(bool(qa[i,u])==bool(qb[j,v]) for u,v in assign.items())
    def choose():
        best=None; opts=None
        for i in range(q):
            if i in assign: continue
            o=[j for j in domains[i] if j not in used and compatible(i,j)]
            if best is None or len(o)<len(opts): best=i; opts=o
        return best,opts
    def singleton_original_pairs(qpairs):
        return {(pa[i][0],pb[j][0]) for i,j in qpairs if len(pa[i])==1 and len(pb[j])==1}
    def rec():
        nonlocal states,witnesses,intersection,limit,no_original_forced
        if limit or no_original_forced: return
        states+=1
        if states>max_quotient_states: limit=True; return
        if len(assign)==q:
            # Direct quotient adjacency check.
            p=np.asarray([assign[i] for i in range(q)],dtype=int)
            if not np.array_equal(qa,qb[np.ix_(p,p)]): return
            w=set(assign.items()); witnesses+=1
            intersection=set(w) if intersection is None else intersection&w
            if not singleton_original_pairs(intersection):
                no_original_forced=True; return
            if witnesses>=max_quotient_witnesses: limit=True
            return
        i,opts=choose()
        if i is None or not opts: return
        for j in opts:
            assign[i]=j; used.add(j); rec(); used.remove(j); del assign[i]
            if limit or no_original_forced: return
    rec()

    if witnesses==0:
        if limit:
            return TwinQuotientCertificate('undetermined_search_limit',(),q,q,0,states,False,'quotient search limit reached before any exact quotient isomorphism')
        return TwinQuotientCertificate('inconsistent_constraints',(),q,q,0,states,True,'no exact quotient isomorphism exists')
    if no_original_forced:
        return TwinQuotientCertificate('certified_no_forced_pairs',(),q,q,witnesses,states,False,'verified quotient alternatives plus within-module automorphisms eliminate every original identity')
    if limit:
        return TwinQuotientCertificate('undetermined_search_limit',(),q,q,witnesses,states,False,'quotient limits reached while singleton-module forced candidates remained')

    qforced=intersection or set(); forced=[]
    for i,j in sorted(qforced):
        if len(pa[i])==1 and len(pb[j])==1:
            forced.append((pa[i][0],pb[j][0]))
    return TwinQuotientCertificate('certified_exact_forced_pairs',tuple(forced),q,q,witnesses,states,True,'complete quotient isomorphism enumeration plus verified twin-module automorphisms')
