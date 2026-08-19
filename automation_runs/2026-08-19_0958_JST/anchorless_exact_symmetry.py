from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
import numpy as np

@dataclass(frozen=True)
class SymmetryCertificate:
    status:str; forced_pairs:tuple[tuple[int,int],...]; witness_pairs:tuple[tuple[int,int],...]; isomorphism_count:int; explored_nodes:int; reason:str

def _validate(graph):
    a=np.asarray(graph[0],dtype=np.int8);x=np.asarray(graph[1]);
    if x.ndim==1:x=x[:,None]
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)) or not np.all((a==0)|(a==1)):raise ValueError('expected simple undirected graph')
    if x.ndim!=2 or len(x)!=len(a):raise ValueError('bad attributes')
    return a,x

def _key(row):return tuple(np.asarray(row).tolist())

def infer_anchorless_exact_forcing(graph_a,graph_b,*,max_search_nodes:int=500_000):
    if max_search_nodes<1:raise ValueError('max_search_nodes must be positive')
    a,x=_validate(graph_a);b,y=_validate(graph_b);n,m=len(a),len(b)
    if n!=m or x.shape[1]!=y.shape[1]:return SymmetryCertificate('inconsistent_constraints',(),(),0,0,'sizes or attribute dimensions differ')
    if Counter(_key(r) for r in x)!=Counter(_key(r) for r in y):return SymmetryCertificate('inconsistent_constraints',(),(),0,0,'attribute inventories differ')
    candidates={i:[j for j in range(n) if _key(x[i])==_key(y[j]) and int(a[i].sum())==int(b[j].sum())] for i in range(n)}
    if any(not c for c in candidates.values()):return SymmetryCertificate('inconsistent_constraints',(),(),0,0,'attribute/degree invariant has empty candidate set')
    order=sorted(range(n),key=lambda i:(len(candidates[i]),-int(a[i].sum()),i));mapping={};used=set();solutions=[];explored=0;cutoff=False
    def dfs(depth):
        nonlocal explored,cutoff
        if cutoff:return
        explored+=1
        if explored>max_search_nodes:cutoff=True;return
        if depth==n:solutions.append(tuple(mapping[i] for i in range(n)));return
        i=order[depth]
        for j in candidates[i]:
            if j in used:continue
            if any(bool(a[i,u])!=bool(b[j,v]) for u,v in mapping.items()):continue
            mapping[i]=j;used.add(j);dfs(depth+1);used.remove(j);del mapping[i]
            if cutoff:return
    dfs(0)
    if cutoff:return SymmetryCertificate('undetermined_search_budget',(),(),len(solutions),explored,'search cutoff reached; no identities released')
    if not solutions:return SymmetryCertificate('inconsistent_constraints',(),(),0,explored,'no exact attributed isomorphism')
    witness=tuple((i,solutions[0][i]) for i in range(n));forced=[]
    for i in range(n):
        vals={s[i] for s in solutions}
        if len(vals)==1:forced.append((i,next(iter(vals))))
    return SymmetryCertificate('certified_forced_pairs' if forced else 'feasible_no_forced_pairs',tuple(forced),witness,len(solutions),explored,'pairs are the intersection of all exact attributed isomorphisms')
