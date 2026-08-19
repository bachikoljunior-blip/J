from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Optional, Tuple

from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from local_certificate_higher_arity_relation_v1 import (
    HigherArityCertificateRelation,
    aggregate_local_certificate_relation,
)
from paired_local_certificate_beard_v1 import paired_local_certificate_beard


@dataclass(frozen=True)
class SignedJohnsonLocalCertificateRelation:
    status: str
    ground_size: int
    subset_size: int
    test_size: int
    test_count: int
    beard_calls: int
    source_relation: Tuple[Tuple[Tuple[int, ...], tuple], ...]
    target_relation: Tuple[Tuple[Tuple[int, ...], tuple], ...]
    source_aggregate: Optional[HigherArityCertificateRelation]
    target_aggregate: Optional[HigherArityCertificateRelation]
    exact: bool
    theorem_scale_recurrence_evidence: bool
    reason: str


def _beard_token(cert):
    if cert.full is None:
        return None
    layers = tuple(
        (
            layer.input_group_order,
            len(layer.affected_before),
            layer.segment_group_order,
            layer.structural_image_order_after,
            layer.giant_type_after,
            len(layer.affected_after),
            layer.quotient_nodes,
            layer.quotient_leaves,
            layer.kernel_leaf_children,
            layer.largest_kernel_child_domain,
            layer.certified_kernel_child_bound,
            layer.recurrence_child_bound_verified,
        )
        for layer in cert.layers
    )
    return (
        "full" if cert.full else "nonfull",
        cert.test_preimage_group_order,
        layers,
    )


def signed_johnson_local_certificate_relation(
    group,
    source_values,
    target_values,
    test_size,
    *,
    max_test_sets=200000,
    max_quotient_leaves=2000000,
    max_child_nodes=200000,
    significant_fraction=0.75,
    design_alpha=0.75,
    max_log_test_factor=4.0,
) -> SignedJohnsonLocalCertificateRelation:
    """Build bounded exact higher-arity local-certificate relations on Johnson ground.

    The certified Johnson lift supplies a generator-paired projection of the
    original candidate group onto ground permutations (the exceptional complement
    bit, when present, remains in the projection kernel).  For every ground test
    set T this routine runs the paired growing-beard certificate against source
    and target strings, converts exact full/nonfull proofs into a label-free
    numerical certificate token, and feeds the complete colored test-set family
    into rev184's higher-arity relation aggregator.

    This is deliberately bounded. If C(v,t) exceeds ``max_test_sets`` or any beard
    call is undetermined, the whole relation fails closed. A later proof-carrying
    orbit/coverage compression may replace exhaustive enumeration, but a sparse
    unproved sample is never treated as a canonical relation here.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    if len(source) != group.degree or len(target) != group.degree:
        raise ValueError("string/group degree mismatch")
    t = int(test_size)
    if t < 5:
        raise ValueError("local-certificate test size must be at least five")

    lift = lift_primitive_johnson_to_ground_relation(group, source, target)
    if lift.status != "exact_johnson_ground_relational_lift":
        return SignedJohnsonLocalCertificateRelation(
            lift.status, lift.ground_size, lift.subset_size, t, 0, 0,
            (), (), None, None, False, False,
            "Johnson ground lift was not certified; local-certificate relation was not attempted",
        )
    v = lift.ground_size
    k = lift.subset_size
    if t > v:
        raise ValueError("test size exceeds Johnson ground size")
    total = comb(v, t)
    if total > max_test_sets:
        return SignedJohnsonLocalCertificateRelation(
            "undetermined_certificate_family_limit", v, k, t, total, 0,
            (), (), None, None, False, False,
            "complete Johnson-ground local-certificate family exceeds max_test_sets; no sparse surrogate was accepted",
        )

    ground_images = tuple(g.ground_permutation for g in lift.lifted_generators)
    source_relation = []
    target_relation = []
    all_theorem_scale = True
    calls = 0
    reuse_target = source == target

    for T in combinations(range(v), t):
        src = paired_local_certificate_beard(
            group, ground_images, source, T,
            max_quotient_leaves=max_quotient_leaves,
            max_child_nodes=max_child_nodes,
        )
        calls += 1
        src_token = _beard_token(src)
        if src_token is None:
            return SignedJohnsonLocalCertificateRelation(
                src.status, v, k, t, total, calls,
                tuple(source_relation), tuple(target_relation), None, None,
                False, False,
                "a source local certificate was undetermined; complete canonical relation construction stopped fail-closed",
            )
        source_relation.append((T, src_token))
        all_theorem_scale = all_theorem_scale and src.theorem_scale_recurrence_evidence

        if reuse_target:
            tgt = src
            tgt_token = src_token
        else:
            tgt = paired_local_certificate_beard(
                group, ground_images, target, T,
                max_quotient_leaves=max_quotient_leaves,
                max_child_nodes=max_child_nodes,
            )
            calls += 1
            tgt_token = _beard_token(tgt)
            if tgt_token is None:
                return SignedJohnsonLocalCertificateRelation(
                    tgt.status, v, k, t, total, calls,
                    tuple(source_relation), tuple(target_relation), None, None,
                    False, False,
                    "a target local certificate was undetermined; complete canonical relation construction stopped fail-closed",
                )
        target_relation.append((T, tgt_token))
        all_theorem_scale = all_theorem_scale and tgt.theorem_scale_recurrence_evidence

    source_agg = aggregate_local_certificate_relation(
        group.degree, v, t, source_relation,
        max_test_sets=max_test_sets,
        significant_fraction=significant_fraction,
        design_alpha=design_alpha,
        max_log_test_factor=max_log_test_factor,
    )
    target_agg = aggregate_local_certificate_relation(
        group.degree, v, t, target_relation,
        max_test_sets=max_test_sets,
        significant_fraction=significant_fraction,
        design_alpha=design_alpha,
        max_log_test_factor=max_log_test_factor,
    )
    exact = bool(source_agg.complete_test_family and target_agg.complete_test_family)
    theorem_scale = bool(
        exact and all_theorem_scale
        and source_agg.theorem_scale_recurrence_evidence
        and target_agg.theorem_scale_recurrence_evidence
    )
    return SignedJohnsonLocalCertificateRelation(
        "exact_signed_johnson_local_certificate_relations" if exact
        else "undetermined_signed_johnson_local_certificate_relations",
        v, k, t, total, calls, tuple(source_relation), tuple(target_relation),
        source_agg, target_agg, exact, theorem_scale,
        "complete source/target Johnson-ground test-set families were colored only by exact paired local certificates and aggregated canonically; theorem-scale evidence remains a separate stronger gate",
    )
