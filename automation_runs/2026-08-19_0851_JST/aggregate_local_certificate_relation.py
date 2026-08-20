from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Tuple

from permutation_group_schreier import identity, schreier_stabilizer_chain
from giant_block_action_certificates import _block_action
from local_fullness_certificates import exact_string_stabilizer, _alternating_test_generators


@dataclass(frozen=True)
class AggregatedCertificateRelation:
    status: str
    quotient_size: int
    test_size: int
    test_count: int
    full_count: int
    nonfull_count: int
    point_colors: Tuple[int, ...]
    color_classes: Tuple[Tuple[int, ...], ...]
    largest_class: int
    significant_split: bool
    refinement_rounds: int
    relation: Tuple[Tuple[Tuple[int, ...], bool], ...]
    reason: str


def _aggregate_boolean_relation(
    quotient_size,
    test_size,
    relation,
    *,
    max_class_fraction,
    reason,
):
    """Canonically refine one complete Boolean t-subset relation.

    Certificate production is deliberately outside this helper.  The bounded
    global-stabilizer oracle and a growing-beard producer can therefore share the
    same canonical incidence aggregation without sharing complexity claims.
    """
    m = int(quotient_size)
    t = int(test_size)
    relation = tuple((tuple(T), bool(full)) for T, full in relation)
    expected = tuple(combinations(range(m), t))
    if tuple(T for T, _ in relation) != expected:
        raise ValueError("relation must contain every t-subset once in canonical order")

    point_colors = [0] * m
    test_colors = [1 if full else 2 for _, full in relation]
    rounds = 0
    while True:
        point_signatures = []
        for u in range(m):
            counts = Counter(test_colors[j] for j, (T, _) in enumerate(relation) if u in T)
            point_signatures.append(("P", point_colors[u], tuple(sorted(counts.items()))))

        test_signatures = []
        for j, (T, full) in enumerate(relation):
            counts = Counter(point_colors[u] for u in T)
            test_signatures.append(("T", int(full), test_colors[j], tuple(sorted(counts.items()))))

        signatures = point_signatures + test_signatures
        labels = {s: i for i, s in enumerate(sorted(set(signatures), key=repr))}
        next_points = [labels[s] for s in point_signatures]
        next_tests = [labels[s] for s in test_signatures]
        rounds += 1
        if next_points == point_colors and next_tests == test_colors:
            break
        point_colors, test_colors = next_points, next_tests
        if rounds > m + len(relation) + 2:
            raise AssertionError("incidence refinement failed to stabilize")

    classes = {}
    for u, color in enumerate(point_colors):
        classes.setdefault(color, []).append(u)
    color_classes = tuple(tuple(v) for _, v in sorted(classes.items()))
    largest = max(map(len, color_classes), default=0)
    significant = len(color_classes) > 1 and largest <= max_class_fraction * m + 1e-12
    return AggregatedCertificateRelation(
        "certified_significant_split" if significant else "canonical_relation_no_significant_split",
        m,
        t,
        len(relation),
        sum(full for _, full in relation),
        sum(not full for _, full in relation),
        tuple(point_colors),
        color_classes,
        largest,
        significant,
        rounds,
        relation,
        reason,
    )


def aggregate_fullness_relation(
    group,
    blocks,
    values,
    *,
    test_size=3,
    max_test_sets=200000,
    max_nodes=500000,
    max_class_fraction=0.9,
) -> AggregatedCertificateRelation:
    """Aggregate exact test-set certificates into a canonical incidence split.

    The global string automorphism group is computed only once. Every t-subset
    receives the canonical Boolean relation "embedded A(T) is contained in the
    quotient image". A deterministic color refinement on the point/test-set
    incidence structure then induces a quotient-point partition. Any reported
    split is therefore invariant under renumbering of the quotient points.

    This implements the split side only. If no color class reduction reaches the
    requested fraction, the routine returns a canonical no-split certificate and
    leaves the Johnson/symmetric obstruction path unresolved.
    """
    blocks = tuple(tuple(b) for b in blocks)
    m = len(blocks)
    t = int(test_size)
    if t < 3 or t > m:
        raise ValueError("test_size must be in [3,m]")
    if not (0 < max_class_fraction < 1):
        raise ValueError("max_class_fraction must be in (0,1)")

    total = comb(m, t)
    if total > max_test_sets:
        return AggregatedCertificateRelation(
            "undetermined_testset_limit", m, t, total, 0, 0, (), (), m, False, 0, (),
            "number of test sets exceeds max_test_sets",
        )

    intersection = exact_string_stabilizer(group, values, max_nodes=max_nodes)
    if intersection.status == "undetermined_node_limit":
        return AggregatedCertificateRelation(
            "undetermined_search_limit", m, t, total, 0, 0, (), (), m, False, 0, (),
            "global string-stabilizer search exceeded max_nodes",
        )
    if intersection.status == "empty_intersection":
        raise AssertionError("identity must stabilize every string")

    aut = intersection.coset.subgroup
    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    eq = identity(m)
    domain_gens = aut.original_generators or (identity(group.degree),)
    image_gens = [_block_action(g, blocks, point_to_block) for g in domain_gens]
    image = schreier_stabilizer_chain(image_gens or [eq])

    relation = []
    for T in combinations(range(m), t):
        full = all(image.contains(q) for q in _alternating_test_generators(m, T))
        relation.append((T, full))

    return _aggregate_boolean_relation(
        m,
        t,
        relation,
        max_class_fraction=max_class_fraction,
        reason="bounded global-stabilizer relation plus canonical colored-incidence refinement",
    )
