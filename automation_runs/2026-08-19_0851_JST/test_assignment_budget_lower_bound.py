from itertools import combinations, permutations
import math
import numpy as np

from assignment_budget_lower_bound import (
    budget_feasible_edge_superset,
    min_cost_cardinality_matching,
)


def brute(costs, left, right, need, forced=()):
    forced=set(forced); best=math.inf; sols=[]
    left=list(left); right=list(right)
    for ls in combinations(left, need):
        for rs in combinations(right, need):
            for p in permutations(rs):
                m=set(zip(ls,p))
                if not forced.issubset(m):
                    continue
                if not all(e in costs for e in m):
                    continue
                c=sum(costs[e] for e in m)
                if c<best:
                    best=c; sols=[m]
                elif c==best:
                    sols.append(m)
    return best, sols


def test_known_total_budget_prunes_edges_that_pairwise_screening_keeps():
    costs={(0,0):1,(0,1):1,(1,0):1,(1,1):1,(2,2):0}
    kept,base=budget_feasible_edge_superset(costs,[0,1,2],[0,1,2],3,1)
    assert not base.feasible or base.minimum_cost==2
    assert kept==()


def test_forced_edge_queries_match_bruteforce():
    costs={(0,0):0,(0,1):3,(1,0):2,(1,1):0,(1,2):1,(2,1):1,(2,2):0}
    for e in costs:
        r=min_cost_cardinality_matching(costs,range(3),range(3),2,forced=(e,))
        b,_=brute(costs,range(3),range(3),2,forced=(e,))
        assert r.minimum_cost==b


def test_random_small_min_cost_and_budget_superset_match_exhaustive():
    rng=np.random.default_rng(92)
    for _ in range(1500):
        nl=int(rng.integers(1,5)); nr=int(rng.integers(1,5)); need=int(rng.integers(0,min(nl,nr)+1))
        costs={}
        for u in range(nl):
            for v in range(nr):
                if rng.random()<0.72:
                    costs[(u,v)]=int(rng.integers(0,5))
        r=min_cost_cardinality_matching(costs,range(nl),range(nr),need)
        b,sols=brute(costs,range(nl),range(nr),need)
        assert r.minimum_cost==b
        budget=int(rng.integers(0,8))
        kept,base=budget_feasible_edge_superset(costs,range(nl),range(nr),need,budget)
        feasible_edges=set()
        if b<=budget:
            for ls in combinations(range(nl),need):
                for rs in combinations(range(nr),need):
                    for p in permutations(rs):
                        m=set(zip(ls,p))
                        if all(e in costs for e in m) and sum(costs[e] for e in m)<=budget:
                            feasible_edges|=m
        assert set(kept)==feasible_edges
