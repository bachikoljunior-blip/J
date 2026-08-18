from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class EssentialMatchingResult:
    maximum_size:int
    matching:Tuple[Tuple[int,int],...]
    essential_edges:Tuple[Tuple[int,int],...]

def hopcroft_karp(adj,left,right):
    left=tuple(left); right=tuple(right); pu={u:None for u in left}; pv={v:None for v in right}; dist={}
    def bfs():
        q=deque(); found=False
        for u in left:
            if pu[u] is None: dist[u]=0; q.append(u)
            else: dist[u]=-1
        while q:
            u=q.popleft()
            for v in adj.get(u,()):
                z=pv.get(v)
                if z is None: found=True
                elif dist[z]<0: dist[z]=dist[u]+1; q.append(z)
        return found
    def dfs(u):
        for v in adj.get(u,()):
            z=pv.get(v)
            if z is None or (dist.get(z,-1)==dist[u]+1 and dfs(z)):
                pu[u]=v; pv[v]=u; return True
        dist[u]=-1; return False
    while bfs():
        for u in left:
            if pu[u] is None: dfs(u)
    return tuple(sorted((u,v) for u,v in pu.items() if v is not None))

def _scc(graph):
    index=0; stack=[]; on=set(); idx={}; low={}; comp={}; cid=0
    def visit(v):
        nonlocal index,cid
        idx[v]=low[v]=index; index+=1; stack.append(v); on.add(v)
        for w in graph.get(v,()):
            if w not in idx: visit(w); low[v]=min(low[v],low[w])
            elif w in on: low[v]=min(low[v],idx[w])
        if low[v]==idx[v]:
            while True:
                w=stack.pop(); on.remove(w); comp[w]=cid
                if w==v: break
            cid+=1
    for v in graph:
        if v not in idx: visit(v)
    return comp

def essential_edges_all_maximum_matchings(adj,left,right):
    left=tuple(left); right=tuple(right); matching=hopcroft_karp(adj,left,right); matched=set(matching); mu={u:v for u,v in matching}; mv={v:u for u,v in matching}
    S=('S',-1); T=('T',-1); L={u:('L',u) for u in left}; R={v:('R',v) for v in right}; g={S:[],T:[]}
    for z in list(L.values())+list(R.values()): g[z]=[]
    for u in left:
        if u in mu: g[L[u]].append(S)
        else: g[S].append(L[u])
    for u in left:
        for v in adj.get(u,()):
            if (u,v) in matched: g[R[v]].append(L[u])
            else: g[L[u]].append(R[v])
    for v in right:
        if v in mv: g[T].append(R[v])
        else: g[R[v]].append(T)
    comp=_scc(g); essential=[]
    for u,v in matching:
        if comp[L[u]]!=comp[R[v]]: essential.append((u,v))
    return EssentialMatchingResult(len(matching),matching,tuple(sorted(essential)))
