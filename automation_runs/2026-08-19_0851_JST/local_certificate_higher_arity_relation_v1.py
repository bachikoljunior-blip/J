from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import ceil, comb, log2
from typing import Hashable, Iterable, Tuple

from babai_local_certificate_parameter_gate_v1 import (
    BabaiLocalCertificateParameterGate,
    babai_local_certificate_parameter_gate,
)


@dataclass(frozen=True)
class HigherArityCertificateRelation:
    status: str
    ground_size: int
    test_size: int
    test_count: int
    relation_rank: int
    complete_test_family: bool
    local_certificate_parameter_gate: BabaiLocalCertificateParameterGate
    logarithmic_test_size_certified: bool
    point_colors: Tuple[int, ...]
    color_classes: Tuple[Tuple[int, ...], ...]
    largest_color_class: int
    significant_point_split: bool
    refinement_rounds: int
    strong_twin_classes: Tuple[Tuple[int, ...], ...]
    largest_strong_symmetric_class: int
    relative_strong_symmetry_defect: float
    design_alpha: float
    design_lemma_parameter_gate: bool
    theorem_scale_recurrence_evidence: bool
    relation: Tuple[Tuple[Tuple[int, ...], Hashable], ...]
    reason: str


def _normalize_relation(ground_size: int, test_size: int, certificate_relation):
    m = int(ground_size)
    k = int(test_size)
    items = []
    seen = set()
    for raw_test, token in certificate_relation:
        T = tuple(sorted(set(int(x) for x in raw_test)))
        if len(T) != k:
            raise ValueError("every certificate test set must contain exactly test_size distinct points")
        if any(x < 0 or x >= m for x in T):
            raise ValueError("certificate test point outside the ground domain")
        if T in seen:
            raise ValueError("duplicate certificate test set")
        try:
            hash(token)
        except TypeError as exc:
            raise ValueError("certificate tokens must be hashable canonical values") from exc
        seen.add(T)
        items.append((T, token))
    return tuple(sorted(items, key=lambda item: item[0]))


def _incidence_refinement(m: int, relation):
    token_labels = {
        token: i
        for i, token in enumerate(sorted({token for _, token in relation}, key=repr))
    }
    point_colors = [0] * m
    test_colors = [token_labels[token] + 1 for _, token in relation]
    rounds = 0
    while True:
        point_signatures = []
        for u in range(m):
            counts = Counter(test_colors[j] for j, (T, _) in enumerate(relation) if u in T)
            point_signatures.append(("P", point_colors[u], tuple(sorted(counts.items()))))
        test_signatures = []
        for j, (T, token) in enumerate(relation):
            counts = Counter(point_colors[u] for u in T)
            test_signatures.append(
                ("T", token_labels[token], test_colors[j], tuple(sorted(counts.items())))
            )
        signatures = point_signatures + test_signatures
        labels = {s: i for i, s in enumerate(sorted(set(signatures), key=repr))}
        next_points = [labels[s] for s in point_signatures]
        next_tests = [labels[s] for s in test_signatures]
        rounds += 1
        if next_points == point_colors and next_tests == test_colors:
            break
        point_colors, test_colors = next_points, next_tests
        if rounds > m + len(relation) + 2:
            raise AssertionError("certificate incidence refinement failed to stabilize")

    classes = {}
    for u, color in enumerate(point_colors):
        classes.setdefault(color, []).append(u)
    return tuple(point_colors), tuple(tuple(xs) for _, xs in sorted(classes.items())), rounds


def _strong_twin_classes(m: int, relation):
    """Compute exact strong-twin classes of a complete colored subset relation."""
    colors = {T: token for T, token in relation}
    parent = list(range(m))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for u in range(m):
        for v in range(u + 1, m):
            ok = True
            for T, token in relation:
                if (u in T) == (v in T):
                    moved = T
                else:
                    moved = tuple(sorted(v if x == u else u if x == v else x for x in T))
                if colors[moved] != token:
                    ok = False
                    break
            if ok:
                union(u, v)

    classes = {}
    for u in range(m):
        classes.setdefault(find(u), []).append(u)
    return tuple(sorted((tuple(xs) for xs in classes.values()), key=lambda xs: (xs[0], len(xs))))


def aggregate_local_certificate_relation(
    primary_domain_size: int,
    ground_size: int,
    test_size: int,
    certificate_relation: Iterable[tuple[Iterable[int], Hashable]],
    *,
    max_test_sets: int = 200000,
    significant_fraction: float = 0.75,
    design_alpha: float = 0.75,
    max_log_test_factor: float = 4.0,
) -> HigherArityCertificateRelation:
    """Aggregate a complete family of canonical local-certificate tokens.

    The intended caller supplies one canonical token for every k-subset of the
    giant ground.  Exact family coverage is required: a sparse sample is not
    relabeling-invariant unless a separate orbit/coverage proof is supplied.  The
    routine keeps three logically separate claims:

    * exactness/canonicality of the colored complete k-subset relation;
    * an incidence-derived significant point split, or a Design-Lemma symmetry
      defect gate for a homogeneous nontrivial relation;
    * theorem-scale recurrence evidence, which additionally requires Babai's
      local-certificate parameter window and an explicit O(log n) test-size cap.

    This separation prevents a small synthetic regression or a resource-limited
    exact relation from being promoted to full quasipolynomial evidence.
    """
    n = int(primary_domain_size)
    m = int(ground_size)
    k = int(test_size)
    if n <= 0 or m <= 0 or not (2 <= k <= m):
        raise ValueError("invalid primary/ground/test parameters")
    if max_test_sets < 1:
        raise ValueError("max_test_sets must be positive")
    if not (0.5 <= float(design_alpha) < 1.0):
        raise ValueError("design_alpha must lie in [1/2,1)")
    if not (0.0 < float(significant_fraction) < 1.0):
        raise ValueError("significant_fraction must lie in (0,1)")
    if max_log_test_factor <= 0:
        raise ValueError("max_log_test_factor must be positive")

    expected = comb(m, k)
    gate = babai_local_certificate_parameter_gate(n, m, k)
    log_cap = max(1, ceil(float(max_log_test_factor) * max(1.0, log2(max(2, n)))))
    log_certified = k <= log_cap

    if expected > max_test_sets:
        return HigherArityCertificateRelation(
            "undetermined_certificate_family_limit", m, k, expected, 0, False,
            gate, log_certified, (), (), m, False, 0, (), m, 0.0,
            float(design_alpha), False, False, (),
            "the complete k-subset certificate family exceeds max_test_sets; no sparse or compressed surrogate was accepted without a separate canonical coverage proof",
        )

    relation = _normalize_relation(m, k, certificate_relation)
    complete = len(relation) == expected
    if not complete:
        return HigherArityCertificateRelation(
            "undetermined_incomplete_certificate_family", m, k, len(relation),
            len({token for _, token in relation}), False, gate, log_certified,
            (), (), m, False, 0, (), m, 0.0, float(design_alpha), False,
            False, relation,
            "not every k-subset has a certificate token; sparse sampling is not promoted to a canonical relation",
        )

    point_colors, color_classes, rounds = _incidence_refinement(m, relation)
    largest_color = max((len(C) for C in color_classes), default=m)
    significant = len(color_classes) > 1 and largest_color <= float(significant_fraction) * m + 1e-12

    strong_classes = _strong_twin_classes(m, relation)
    largest_strong = max((len(C) for C in strong_classes), default=1)
    defect = (m - largest_strong) / float(m)
    alpha = float(design_alpha)
    design_gate = bool(2 <= k <= m / 2 and defect + 1e-12 >= 1.0 - alpha)
    rank = len({token for _, token in relation})
    theorem_scale = bool(gate.certified and log_certified and (significant or (rank > 1 and design_gate)))

    if significant:
        status = "certified_significant_point_split"
        reason = "complete canonical certificate relation has a label-invariant significant incidence partition"
    elif rank <= 1:
        status = "uniform_certificate_relation_no_progress"
        reason = "complete certificate relation is uniform; incidence and Design-Lemma input carry no nontrivial certificate color"
    elif design_gate:
        status = "certified_higher_arity_relation_for_design_lemma"
        reason = "complete nontrivial certificate relation has no significant point split but satisfies the exact strong-symmetry-defect parameter gate for Design-Lemma descent"
    else:
        status = "higher_arity_relation_without_design_gate"
        reason = "complete nontrivial certificate relation was built, but its arity/symmetry defect does not certify the Design-Lemma hypothesis"

    if not theorem_scale:
        reason += "; theorem-scale recurrence evidence remains false unless the local-certificate parameter window, logarithmic test-size gate, and a certified split/Design input all hold"

    return HigherArityCertificateRelation(
        status, m, k, expected, rank, True, gate, log_certified,
        point_colors, color_classes, largest_color, significant, rounds,
        strong_classes, largest_strong, defect, alpha, design_gate,
        theorem_scale, relation, reason,
    )
