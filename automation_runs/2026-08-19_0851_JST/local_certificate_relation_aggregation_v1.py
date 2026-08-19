from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import floor


@dataclass(frozen=True)
class LocalCertificateRelationAggregation:
    status: str
    quotient_degree: int
    arity: int
    relation_rank: int
    test_sets_checked: int
    expected_test_sets: int
    point_cells: tuple[tuple[int, ...], ...]
    largest_point_cell: int
    significant_split: bool
    reason: str


def local_certificate_beard_token(cert):
    """Project an exact beard result to relabeling-invariant mathematical data.

    Raw test-set labels, affected-point identities, traversal node counts and leaf
    counts are deliberately excluded.  Subgroup orders, affected-set cardinalities,
    giant type and certified recurrence bounds are preserved under conjugating the
    whole instance by a domain relabeling and are therefore safe relation colors.
    """
    final_order = None if cert.final_group is None else int(cert.final_group.order)
    full_order = (
        None
        if cert.full_automorphism_subgroup is None
        else int(cert.full_automorphism_subgroup.order)
    )
    layers = tuple(
        (
            int(layer.input_group_order),
            len(tuple(layer.affected_before)),
            int(layer.segment_group_order),
            layer.giant_type_after,
            len(tuple(layer.affected_after)),
            int(layer.largest_kernel_child_domain),
            int(layer.certified_kernel_child_bound),
            bool(layer.recurrence_child_bound_verified),
        )
        for layer in cert.layers
    )
    return (
        str(cert.status),
        cert.full,
        int(cert.test_preimage_group_order),
        final_order,
        full_order,
        bool(cert.parameter_gate.certified),
        layers,
    )


def aggregate_local_certificate_relation(
    quotient_degree: int,
    test_sets,
    relation_tokens,
    *,
    shrink_fraction: float = 0.9,
):
    """Aggregate all t-local certificate colors into a canonical point split.

    The caller must provide the complete family of t-subsets of the quotient.
    Each t-subset is colored by a relabeling-invariant certificate token.  We then
    color each quotient point by its incidence histogram with relation colors.
    This is a canonical one-step projection of the higher-arity relation.  If the
    resulting point partition has more than one cell and every cell is at most a
    fixed fraction of the quotient, it is a verified significant split.  If point
    profiles remain homogeneous while the higher-arity relation is nontrivial, the
    function preserves that obstruction explicitly for a later Design-Lemma-style
    descent rather than inventing a split.

    Partial t-subset coverage is rejected fail-closed because sampling selected test
    sets would make the result depend on an external naming/order choice.
    """
    m = int(quotient_degree)
    if m <= 0:
        raise ValueError("quotient_degree must be positive")
    if not (0.0 < float(shrink_fraction) < 1.0):
        raise ValueError("shrink_fraction must lie in (0,1)")

    sets = tuple(tuple(sorted(set(int(x) for x in T))) for T in test_sets)
    tokens = tuple(relation_tokens)
    if len(sets) != len(tokens):
        raise ValueError("test_sets and relation_tokens length mismatch")
    if not sets:
        return LocalCertificateRelationAggregation(
            "empty_local_certificate_relation", m, 0, 0, 0, 0, (), 0, False,
            "no local certificate relation was supplied",
        )
    t = len(sets[0])
    if t <= 0 or t > m or any(len(T) != t for T in sets):
        raise ValueError("all test sets must have one common positive arity <= quotient degree")
    if any(x < 0 or x >= m for T in sets for x in T):
        raise ValueError("test-set point outside quotient")
    if len(set(sets)) != len(sets):
        raise ValueError("duplicate test set")

    expected_family = tuple(combinations(range(m), t))
    expected_count = len(expected_family)
    by_set = dict(zip(sets, tokens))
    if len(by_set) != expected_count or any(T not in by_set for T in expected_family):
        return LocalCertificateRelationAggregation(
            "incomplete_local_certificate_relation", m, t, 0, len(sets),
            expected_count, (), 0, False,
            "the complete t-subset certificate relation is required for canonical aggregation",
        )

    # Tokens are opaque hashable mathematical invariants.  Deterministic repr-order
    # is used only to assign temporary integer color names; equality classes, which
    # determine every returned cell, do not depend on these integer names.
    unique_tokens = sorted(set(tokens), key=repr)
    labels = {token: i for i, token in enumerate(unique_tokens)}
    rank = len(unique_tokens)

    point_profiles = []
    for x in range(m):
        counts = Counter(labels[by_set[T]] for T in expected_family if x in T)
        point_profiles.append(tuple(sorted(counts.items())))

    cells_by_profile = defaultdict(list)
    for x, profile in enumerate(point_profiles):
        cells_by_profile[profile].append(x)
    cells = tuple(
        sorted(
            (tuple(points) for points in cells_by_profile.values()),
            key=lambda C: (len(C), C),
        )
    )
    largest = max((len(C) for C in cells), default=0)
    significant_limit = max(1, floor(float(shrink_fraction) * m))
    significant = len(cells) > 1 and largest <= significant_limit

    if rank <= 1:
        return LocalCertificateRelationAggregation(
            "homogeneous_trivial_local_certificate_relation", m, t, rank,
            len(sets), expected_count, cells, largest, False,
            "all local certificate test sets have one relation color, so this aggregation supplies no structural split",
        )
    if significant:
        return LocalCertificateRelationAggregation(
            "canonical_significant_point_split_from_local_certificates", m, t,
            rank, len(sets), expected_count, cells, largest, True,
            "incidence profiles of the complete canonical higher-arity certificate relation produce a label-invariant significant quotient-point partition",
        )
    if len(cells) > 1:
        return LocalCertificateRelationAggregation(
            "canonical_nonsignificant_point_split_from_local_certificates", m,
            t, rank, len(sets), expected_count, cells, largest, False,
            "the higher-arity certificate relation distinguishes quotient points but the largest cell does not meet the configured significant-shrink bound",
        )
    return LocalCertificateRelationAggregation(
        "homogeneous_nontrivial_local_certificate_relation_requires_design_descent",
        m, t, rank, len(sets), expected_count, cells, largest, False,
        "the complete local-certificate relation is nontrivial but all point incidence profiles are equal; preserve the higher-arity relation for Design-Lemma-style descent",
    )
