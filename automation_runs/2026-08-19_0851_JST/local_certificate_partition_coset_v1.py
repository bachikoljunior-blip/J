from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aggregate_local_certificate_relation import (
    AggregatedCertificateRelation,
    aggregate_fullness_relation,
)
from canonical_partition_transporter_v1 import (
    CanonicalPartitionTransport,
    canonical_partition_transporter,
)
from permutation_group_schreier import Permutation, StabilizerChain


@dataclass(frozen=True)
class LocalCertificatePartitionCoset:
    status: str
    source_relation: AggregatedCertificateRelation
    target_relation: AggregatedCertificateRelation
    transport: Optional[CanonicalPartitionTransport]
    source_stabilizer: Optional[StabilizerChain]
    transporter: Optional[Permutation]
    candidate_count: int
    reason: str


def local_certificate_partition_coset(
    group: StabilizerChain,
    blocks,
    source_values,
    target_values,
    *,
    test_size=3,
    max_test_sets=200000,
    max_nodes=500000,
    max_class_fraction=0.9,
    max_partition_states=200000,
) -> LocalCertificatePartitionCoset:
    """Return the exact ambient coset respecting two canonical local partitions.

    Each string independently receives the exact rev115-116 fullness relation and
    canonical incidence refinement.  When both yield significant ordered color
    partitions, rev146 constructs an exact full-domain transporter t and the
    exact source partition stabilizer H.  The partition-respecting candidates are
    exactly {h then t : h in H} under this repository's right-action convention.

    This is deliberately a *partition* coset, not yet the final string-isomorphism
    coset.  Later recursion must filter it by the child strings.  Resource limits,
    missing significant structure, incompatible canonical shapes, and unreachable
    target partitions all fail closed and never manufacture candidates.
    """
    source = aggregate_fullness_relation(
        group,
        blocks,
        source_values,
        test_size=test_size,
        max_test_sets=max_test_sets,
        max_nodes=max_nodes,
        max_class_fraction=max_class_fraction,
    )
    target = aggregate_fullness_relation(
        group,
        blocks,
        target_values,
        test_size=test_size,
        max_test_sets=max_test_sets,
        max_nodes=max_nodes,
        max_class_fraction=max_class_fraction,
    )

    for side, relation in (("source", source), ("target", target)):
        if relation.status.startswith("undetermined_"):
            return LocalCertificatePartitionCoset(
                relation.status,
                source,
                target,
                None,
                None,
                None,
                0,
                f"{side} canonical local-certificate construction exceeded a certified resource bound",
            )

    if not source.significant_split or not target.significant_split:
        status = (
            "canonical_local_partition_unavailable"
            if source.significant_split == target.significant_split
            else "canonical_local_partition_incompatible"
        )
        return LocalCertificatePartitionCoset(
            status,
            source,
            target,
            None,
            None,
            None,
            0,
            "both strings must expose corresponding significant canonical local-certificate partitions before coset recursion",
        )

    if tuple(map(len, source.color_classes)) != tuple(map(len, target.color_classes)):
        return LocalCertificatePartitionCoset(
            "canonical_local_partition_shape_mismatch",
            source,
            target,
            None,
            None,
            None,
            0,
            "ordered canonical local-certificate cells have different sizes",
        )

    transport = canonical_partition_transporter(
        group,
        blocks,
        source.color_classes,
        target.color_classes,
        max_states=max_partition_states,
    )
    if transport.status != "partition_transporter_coset":
        return LocalCertificatePartitionCoset(
            transport.status,
            source,
            target,
            transport,
            transport.source_stabilizer,
            None,
            0,
            "no certified ambient partition-respecting coset is available",
        )

    stabilizer = transport.source_stabilizer
    if stabilizer is None or transport.transporter is None:
        raise AssertionError("successful partition transporter must provide subgroup and representative")
    return LocalCertificatePartitionCoset(
        "canonical_local_partition_coset",
        source,
        target,
        transport,
        stabilizer,
        transport.transporter,
        stabilizer.order,
        "exact ambient coset of candidates mapping each source canonical local-certificate cell to its target counterpart",
    )
