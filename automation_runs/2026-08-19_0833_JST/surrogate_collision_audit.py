from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Tuple
import numpy as np

from wl_attributed_kernel import wl_attributed_feature_map


@dataclass(frozen=True)
class CollisionAudit:
    status: str
    require_escalation: bool
    surrogate_equal: bool
    differing_invariants: Tuple[str, ...]
    reason: str


def _components(a: np.ndarray) -> Tuple[int, ...]:
    n = a.shape[0]
    seen = np.zeros(n, dtype=bool)
    sizes: List[int] = []
    for root in range(n):
        if seen[root]:
            continue
        stack = [root]
        seen[root] = True
        size = 0
        while stack:
            i = stack.pop(); size += 1
            for j in np.flatnonzero(a[i]):
                if not seen[j]:
                    seen[j] = True; stack.append(int(j))
        sizes.append(size)
    return tuple(sorted(sizes))


def _triangle_count(a: np.ndarray) -> int:
    ai = a.astype(np.int64)
    return int(np.trace(ai @ ai @ ai) // 6)


def _four_cycle_walk_moment(a: np.ndarray) -> int:
    ai = a.astype(np.int64)
    a2 = ai @ ai
    return int(np.sum(a2 * a2.T))


def structural_fingerprint(adjacency: np.ndarray) -> Dict[str, object]:
    a = (np.asarray(adjacency) != 0)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("adjacency must be square")
    if not np.array_equal(a, a.T) or np.any(np.diag(a)):
        raise ValueError("expected a simple undirected graph")
    return {
        "n": int(a.shape[0]),
        "m": int(a.sum() // 2),
        "degree_multiset": tuple(sorted(int(v) for v in a.sum(axis=1))),
        "component_sizes": _components(a),
        "triangles": _triangle_count(a),
        "trace_a4": _four_cycle_walk_moment(a),
    }


def _features_close(fa: Mapping, fb: Mapping, *, atol: float = 1e-10, rtol: float = 1e-9) -> bool:
    if fa.keys() != fb.keys():
        return False
    return all(np.isclose(fa[k], fb[k], atol=atol, rtol=rtol) for k in fa)


def audit_surrogate_pair(graph_a, graph_b, *, iterations: int = 3,
                         rff_components: int = 32, bandwidth: float = 1.0,
                         seed: int = 0, require_identity_decision: bool = True) -> CollisionAudit:
    fa = wl_attributed_feature_map(graph_a[0], graph_a[1], iterations=iterations,
                                   rff_components=rff_components, bandwidth=bandwidth, seed=seed)
    fb = wl_attributed_feature_map(graph_b[0], graph_b[1], iterations=iterations,
                                   rff_components=rff_components, bandwidth=bandwidth, seed=seed)
    equal = _features_close(fa, fb)
    if not equal:
        return CollisionAudit("certified_distinct_by_invariant", False, False, (),
                              "permutation-invariant feature maps differ")
    sa, sb = structural_fingerprint(graph_a[0]), structural_fingerprint(graph_b[0])
    diff = tuple(k for k in sa if sa[k] != sb[k])
    if diff:
        return CollisionAudit("surrogate_collision_detected", True, True, diff,
                              "surrogate agrees but exact structural invariants differ")
    if require_identity_decision:
        return CollisionAudit("undetermined_fail_closed", True, True, (),
                              "matching surrogate/fingerprint is not a complete isomorphism certificate")
    return CollisionAudit("surrogate_match_unverified", False, True, (),
                          "identity was not requested; equality remains unverified")
