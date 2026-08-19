from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional

from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from paired_partition_transporter_v1 import paired_partition_transporter
from signed_johnson_local_certificate_relation_v1 import (
    SignedJohnsonLocalCertificateRelation,
    signed_johnson_local_certificate_relation,
)


@dataclass(frozen=True)
class SignedJohnsonLocalCertificateSplitFilter:
    status: str
    coset: Optional[RightCoset]
    relation: SignedJohnsonLocalCertificateRelation
    partition_orbit_states: int
    exact_empty: bool
    canonical_filter: bool
    theorem_scale_recurrence_evidence: bool
    reason: str


def signed_johnson_local_certificate_split_filter(
    group,
    source_values,
    target_values,
    test_size,
    *,
    max_test_sets=200000,
    max_quotient_leaves=2000000,
    max_child_nodes=200000,
    max_partition_states=200000,
    significant_fraction=0.75,
    design_alpha=0.75,
    max_log_test_factor=4.0,
) -> SignedJohnsonLocalCertificateSplitFilter:
    """Turn a certified local-certificate incidence split into an original coset filter.

    Every original Johnson isomorphism induces a ground permutation preserving the
    complete colored test-set certificate relation.  Therefore it must preserve
    the canonical point refinement of that relation.  When rev184 obtains a
    significant ordered point partition on both source and target, this routine
    solves the exact partition transporter inside the generator-paired Johnson
    ground action and lifts the complete transporter coset back to the original
    k-subset domain.

    This is a necessary structural filter, not by itself a full-string SI result.
    Exact emptiness *is* promotable when certificate-token multiplicities or the
    canonical partition transporter disagree, because every true isomorphism must
    preserve those invariants. Homogeneous Design-Lemma inputs are surfaced but
    remain open for the subsequent proof-carrying design descent.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    relation = signed_johnson_local_certificate_relation(
        group, source, target, test_size,
        max_test_sets=max_test_sets,
        max_quotient_leaves=max_quotient_leaves,
        max_child_nodes=max_child_nodes,
        significant_fraction=significant_fraction,
        design_alpha=design_alpha,
        max_log_test_factor=max_log_test_factor,
    )
    if not relation.exact or relation.source_aggregate is None or relation.target_aggregate is None:
        return SignedJohnsonLocalCertificateSplitFilter(
            relation.status, None, relation, 0, False, False, False,
            "complete exact local-certificate relations were unavailable; split filtering did not proceed",
        )

    source_mult = Counter(token for _, token in relation.source_relation)
    target_mult = Counter(token for _, token in relation.target_relation)
    if source_mult != target_mult:
        return SignedJohnsonLocalCertificateSplitFilter(
            "exact_empty_local_certificate_token_multiplicity", None, relation,
            0, True, True, relation.theorem_scale_recurrence_evidence,
            "source and target complete certificate relations have different canonical token multiplicities",
        )

    sa = relation.source_aggregate
    ta = relation.target_aggregate
    ssplit = sa.significant_point_split
    tsplit = ta.significant_point_split
    if ssplit != tsplit:
        return SignedJohnsonLocalCertificateSplitFilter(
            "exact_empty_local_certificate_split_invariant", None, relation, 0,
            True, True, relation.theorem_scale_recurrence_evidence,
            "only one complete certificate relation has the canonical significant point split; the relations cannot be isomorphic",
        )

    if not ssplit:
        if (
            sa.status == "certified_higher_arity_relation_for_design_lemma"
            and ta.status == "certified_higher_arity_relation_for_design_lemma"
        ):
            return SignedJohnsonLocalCertificateSplitFilter(
                "verified_homogeneous_local_certificate_design_input", None,
                relation, 0, False, True,
                relation.theorem_scale_recurrence_evidence,
                "both complete nontrivial certificate relations pass the exact Design-Lemma symmetry-defect gate; proof-carrying design descent remains the active child",
            )
        return SignedJohnsonLocalCertificateSplitFilter(
            "local_certificate_relation_without_significant_split", None,
            relation, 0, False, True,
            relation.theorem_scale_recurrence_evidence,
            "complete local-certificate relations are exact but do not yet provide a significant point partition or paired Design input",
        )

    if tuple(map(len, sa.color_classes)) != tuple(map(len, ta.color_classes)):
        return SignedJohnsonLocalCertificateSplitFilter(
            "exact_empty_local_certificate_partition_shape", None, relation, 0,
            True, True, relation.theorem_scale_recurrence_evidence,
            "ordered canonical point-color cell sizes differ",
        )

    lift = lift_primitive_johnson_to_ground_relation(group, source, target)
    if lift.status != "exact_johnson_ground_relational_lift":
        raise AssertionError("exact certificate relation unexpectedly lost its Johnson ground lift")
    ground_images = tuple(g.ground_permutation for g in lift.lifted_generators)
    transport = paired_partition_transporter(
        group, ground_images, sa.color_classes, ta.color_classes,
        max_states=max_partition_states,
    )
    if transport.status in {"partition_shape_mismatch", "no_partition_transporter"}:
        return SignedJohnsonLocalCertificateSplitFilter(
            "exact_empty_local_certificate_partition_transporter", None,
            relation, transport.orbit_states, True, True,
            relation.theorem_scale_recurrence_evidence,
            "canonical significant point partitions have no transporter in the certified Johnson ground image",
        )
    if transport.status == "undetermined_partition_orbit_limit":
        return SignedJohnsonLocalCertificateSplitFilter(
            transport.status, None, relation, transport.orbit_states, False,
            False, False,
            "canonical point-partition transporter search exceeded its exact state budget",
        )
    if transport.status != "exact_paired_partition_transporter_coset" or transport.lifted_coset is None:
        raise AssertionError("unexpected paired partition transporter status")

    return SignedJohnsonLocalCertificateSplitFilter(
        "verified_local_certificate_partition_filter",
        transport.lifted_coset, relation, transport.orbit_states, False, True,
        relation.theorem_scale_recurrence_evidence,
        "complete certificate incidence produced a significant canonical ground partition whose entire transporter coset was lifted exactly to the original Johnson domain",
    )
