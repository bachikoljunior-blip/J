from itertools import combinations,permutations
import numpy as np
from essential_matching_scc import essential_edges_all_maximum_matchings

def brute(adj,left,right):
    left=list(left); right=list(right); sols=[]; best=-1
    for k in range(min(len(left),len(right))+1):
        for ls in combinations(left,k):
            for rs in combinations(right,k):
                for p in permutations(rs):
                    s=set(zip(ls,p))
                    if all(v in adj.get(u,()) for u,v in s):
                        if k>best: best=k; sols=[s]
                        elif k==best: sols.append(s)
    forced=set(sols[0]) if sols else set()
    for s in sols[1:]: forced&=s
    return best,forced

def test_complete_2x2_has_no_essential_edges():
    r=essential_edges_all_maximum_matchings({0:[0,1],1:[0,1]},[0,1],[0,1]); assert r.maximum_size==2 and r.essential_edges==()

def test_unique_matching_all_essential():
    r=essential_edges_all_maximum_matchings({0:[0],1:[1],2:[2]},[0,1,2],[0,1,2]); assert set(r.essential_edges)=={(0,0),(1,1),(2,2)}

def test_random_small_matches_exhaustive_all_maximum_semantics():
    rng=np.random.default_rng(91)
    for _ in range(1200):
        nl=int(rng.integers(1,5)); nr=int(rng.integers(1,5)); adj={u:[v for v in range(nr) if rng.random()<0.45] for u in range(nl)}; best,forced=brute(adj,range(nl),range(nr)); r=essential_edges_all_maximum_matchings(adj,range(nl),range(nr)); assert r.maximum_size==best and set(r.essential_edges)==forced
