from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Dict, List, Mapping, Sequence, Tuple
import math
import numpy as np


def _validate_adjacency(adjacency: np.ndarray) -> np.ndarray:
    a = np.asarray(adjacency)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("adjacency must be square")
    if a.shape[0] == 0:
        raise ValueError("graph must contain at least one node")
    if not np.all(np.isfinite(a)):
        raise ValueError("adjacency contains non-finite values")
    a = (a != 0)
    if not np.array_equal(a, a.T):
        raise ValueError("only undirected graphs are supported")
    if np.any(np.diag(a)):
        raise ValueError("self-loops are not supported")
    return a


def _validate_attributes(attributes: np.ndarray, n: int) -> np.ndarray:
    x = np.asarray(attributes, dtype=float)
    if x.ndim != 2 or x.shape[0] != n:
        raise ValueError("attributes must have shape (n_nodes, attribute_dim)")
    if x.shape[1] == 0:
        raise ValueError("attribute_dim must be positive")
    if not np.all(np.isfinite(x)):
        raise ValueError("attributes contain non-finite values")
    return x


def _digest(parts: Sequence[bytes], *, digest_size: int = 16) -> bytes:
    h = blake2b(digest_size=digest_size, person=b"agi-wl-v1")
    for part in parts:
        h.update(len(part).to_bytes(4, "little", signed=False))
        h.update(part)
    return h.digest()


def _initial_colors(a: np.ndarray) -> List[bytes]:
    deg = a.sum(axis=1).astype(int)
    return [_digest([b"deg", int(d).to_bytes(8, "little", signed=False)]) for d in deg]


def _refine_colors(a: np.ndarray, colors: Sequence[bytes]) -> List[bytes]:
    out: List[bytes] = []
    for i in range(a.shape[0]):
        neigh = [colors[j] for j in np.flatnonzero(a[i])]
        neigh.sort()
        out.append(_digest([b"self", colors[i], b"neigh", *neigh]))
    return out


@dataclass(frozen=True)
class RFFConfig:
    attribute_dim: int
    components: int = 32
    bandwidth: float = 1.0
    seed: int = 0

    def matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        if self.attribute_dim < 1 or self.components < 1:
            raise ValueError("attribute_dim/components must be positive")
        if not (self.bandwidth > 0.0 and math.isfinite(self.bandwidth)):
            raise ValueError("bandwidth must be finite and positive")
        rng = np.random.default_rng(self.seed)
        w = rng.normal(0.0, 1.0 / self.bandwidth,
                       size=(self.components, self.attribute_dim))
        b = rng.uniform(0.0, 2.0 * np.pi, size=self.components)
        return w, b


def _rff(x: np.ndarray, config: RFFConfig) -> np.ndarray:
    if x.shape[1] != config.attribute_dim:
        raise ValueError("attribute dimension does not match RFFConfig")
    w, b = config.matrices()
    return math.sqrt(2.0 / config.components) * np.cos(x @ w.T + b)


def wl_attributed_feature_map(adjacency: np.ndarray, attributes: np.ndarray, *,
                              iterations: int = 3, rff_components: int = 32,
                              bandwidth: float = 1.0, seed: int = 0,
                              normalize_node_mass: bool = True) -> Dict[Tuple[int, bytes, int], float]:
    """Polynomial-time permutation-invariant attributed-graph feature map.

    It is a scalable surrogate, not a complete graph-isomorphism invariant:
    1-WL collisions and digest collisions remain possible.
    """
    if iterations < 0:
        raise ValueError("iterations must be non-negative")
    a = _validate_adjacency(adjacency)
    x = _validate_attributes(attributes, a.shape[0])
    config = RFFConfig(x.shape[1], rff_components, bandwidth, seed)
    z = _rff(x, config)
    colors = _initial_colors(a)
    features: Dict[Tuple[int, bytes, int], float] = {}
    mass_scale = 1.0 / math.sqrt(a.shape[0]) if normalize_node_mass else 1.0
    for depth in range(iterations + 1):
        buckets: Dict[bytes, np.ndarray] = {}
        for i, color in enumerate(colors):
            if color not in buckets:
                buckets[color] = np.zeros(rff_components, dtype=float)
            buckets[color] += z[i]
        for color, vec in buckets.items():
            vec = vec * mass_scale
            for k, value in enumerate(vec):
                if value != 0.0:
                    features[(depth, color, k)] = float(value)
        if depth < iterations:
            colors = _refine_colors(a, colors)
    return features


def _dot_sparse(a: Mapping[Tuple[int, bytes, int], float], b: Mapping[Tuple[int, bytes, int], float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return float(sum(v * b.get(k, 0.0) for k, v in a.items()))


def _norm_sparse(a: Mapping[Tuple[int, bytes, int], float]) -> float:
    return math.sqrt(max(_dot_sparse(a, a), 0.0))


def wl_attributed_kernel(graph_a: Tuple[np.ndarray, np.ndarray],
                         graph_b: Tuple[np.ndarray, np.ndarray], *,
                         iterations: int = 3, rff_components: int = 32,
                         bandwidth: float = 1.0, seed: int = 0,
                         normalized: bool = True) -> float:
    fa = wl_attributed_feature_map(graph_a[0], graph_a[1], iterations=iterations,
                                   rff_components=rff_components, bandwidth=bandwidth, seed=seed)
    fb = wl_attributed_feature_map(graph_b[0], graph_b[1], iterations=iterations,
                                   rff_components=rff_components, bandwidth=bandwidth, seed=seed)
    value = _dot_sparse(fa, fb)
    if not normalized:
        return value
    denom = _norm_sparse(fa) * _norm_sparse(fb)
    return 0.0 if denom <= 1e-15 else float(value / denom)


def gram_matrix(graphs: Sequence[Tuple[np.ndarray, np.ndarray]], *,
                iterations: int = 3, rff_components: int = 32,
                bandwidth: float = 1.0, seed: int = 0,
                normalized: bool = True) -> np.ndarray:
    features = [wl_attributed_feature_map(a, x, iterations=iterations,
                rff_components=rff_components, bandwidth=bandwidth, seed=seed)
                for a, x in graphs]
    n = len(features)
    out = np.empty((n, n), dtype=float)
    norms = [_norm_sparse(f) for f in features]
    for i in range(n):
        for j in range(i, n):
            v = _dot_sparse(features[i], features[j])
            if normalized:
                denom = norms[i] * norms[j]
                v = 0.0 if denom <= 1e-15 else v / denom
            out[i, j] = out[j, i] = v
    return out
