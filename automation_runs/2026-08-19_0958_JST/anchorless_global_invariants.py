from __future__ import annotations
from dataclasses import dataclass
from collections import Counter,deque
import numpy as np

@dataclass(frozen=True)
class InvariantSymmetryCertificate:
    status:str;forced_pairs:tuple[tuple[int,int],...];witness_pairs:tuple[tuple[int,int],...];singleton_signature_pairs:int;explored_nodes:int;reason:str

def _validate(graph):
    a=np.asarray(graph[0],dtype=np.int8);x=np.asarray(graph[1]);
    if x.ndim==1:x=x[:,None]
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)) or not np.all((a==0)|(a==1)):raise ValueError('expected simple undirected graph')
    if x.ndim!=2 or len(x)!=len(a):raise ValueError('bad attributes')
    return a,x

def _akey(row):return tuple(np.asarray(row).tolist())
def _all_distances(adj,src):
    n=len(adj);dist=[-1]*n;dist[src]=0;q=deque([src])
    while q:
        u=q.popleft()
        for v in np.flatnonzero(adj[u]):
            v=int(v)
            if dist[v]<0:dist[v]=dist[u]+1;q.append(v)
    return dist

def _signatures(adj,attrs,keys):
    n=len(adj);key_of=[_akey(r) for r in attrs];out=[]
    for u in range(n):
        dist=_all_distances(adj,u);by=[]
        for k in keys:
            hist=Counter(dist[v] for v in range(n) if key_of[v]==k);by.append((k,tuple(sorted(hist.items()))))
        nbr_deg=tuple(sorted(int(adj[v].sum()) for v in np.flatnonzero(adj[u])));out.append((key_of[u],int(adj[u].sum()),tuple(by),nbr_deg))
    return out

def infer_anchorless_invariant_forcing(graph_a,graph_b,*,max_search_nodes:int=300_000):
    if max_search_nodes<1:raise ValueError('max_search_nodes must be positive')
    a,x=_validate(graph_a);b,y=_validate(graph_b);n,m=len(a),len(b)
    if n!=m or x.shape[1]!=y.shape[1]:return InvariantSymmetryCertificate('inconsistent_constraints',(),(),0,0,'sizes or attribute dimensions differ')
    keys=tuple(sorted(set(_akey(r) for r in x)|set(_akey(r) for r in y),key=repr));sx=_signatures(a,x,keys);sy=_signatures(b,y,keys);cx=Counter(sx);cy=Counter(sy)
    if cx!=cy:return InvariantSymmetryCertificate('inconsistent_constraints',(),(),0,0,'global invariant inventories differ')
    target={s:[] for s in cy}
    for j,s in enumerate(sy):target[s].append(j)
    candidates={i:tuple(target[sx[i]]) for i in range(n)};singleton={i:candidates[i][0] for i in range(n) if len(candidates[i])==1};order=sorted(range(n),key=lambda i:(len(candidates[i]),-int(a[i].sum()),i));mapping={};used=set();explored=0;cutoff=False;witness=None
    def dfs(depth):
        nonlocal explored,cutoff,witness
        if witness is not None or cutoff:return
        explored+=1
        if explored>max_search_nodes:cutoff=True;return
        if depth==n:witness=tuple(mapping[i] for i in range(n));return
        i=order[depth]
        for j in candidates[i]:
            if j in used or any(bool(a[i,u])!=bool(b[j,v]) for u,v in mapping.items()):continue
            mapping[i]=j;used.add(j);dfs(depth+1);used.remove(j);del mapping[i]
            if witness is not None or cutoff:return
    dfs(0)
    if witness is None:return InvariantSymmetryCertificate('undetermined_search_budget' if cutoff else 'inconsistent_constraints',(),(),len(singleton),explored,'no witness before search cutoff; no identities released' if cutoff else 'invariants compatible but no exact isomorphism exists')
    return InvariantSymmetryCertificate('certified_forced_pairs' if singleton else 'feasible_no_forced_pairs',tuple(sorted(singleton.items())),tuple((i,witness[i]) for i in range(n)),len(singleton),explored,'singleton exact global-invariant cells are forced after direct exact-isomorphism witness verification')
