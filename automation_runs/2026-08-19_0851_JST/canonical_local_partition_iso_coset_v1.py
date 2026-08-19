from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aggregate_local_certificate_relation import (
    AggregatedCertificateRelation,
    aggregate_fullness_relation,
)
from canonical_partition_transporter_v1 import canonical_partition_transporter
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import (
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
)


@dataclass(frozen=True)
class CanonicalLocalPartitionIsoCoset:
    status: str
    source_relation: AggregatedCertificateRelation
    target_relation: AggregatedCertificateRelation
    candidate_coset: Optional[RightCoset]
    partition_orbit_states: int
    reason: str


def _target_stabilizer(source_stabilizer, transporter):
    """Conjugate source partition stabilizer to the target partition stabilizer."""
    r = transporter
    e = identity(source_stabilizer.degree)
    gens = source_stabilizer.original_generators or (e,)
    # compose(a,b) = b o a.  We need r h r^-1 in ordinary function notation.
    conjugates = [compose(compose(inverse(r), h), r) for h in gens]
    return schreier_stabilizer_chain(conjugates or [e])


def canonical_local_partition_iso_coset(
    group,
    blocks,
    source_values,
    target_values,
    *,
    test_size=3,
    max_test_sets=200000,
    max_nodes=500000,
    max_class_fraction=0.9,
    max_partition_states=200000,
) -> CanonicalLocalPartitionIsoCoset:
    """Canonical-partition prefilter/coset for two-string isomorphism.

    Both strings are independently passed through the same rev116 canonical
    local-certificate construction.  Under a true G-isomorphism their stable
    color IDs and ordered color classes agree up to the induced G action.  A
    significant partition is therefore safe to use as an invariant prefilter.

    If both sides expose a significant partition, rev146 computes an exact
    ambient transporter.  The returned RightCoset uses the target partition
    stabilizer, matching RightCoset.contains' convention.  This is only a
    partition-respecting candidate coset; it is not yet the final string
    isomorphism coset.
    """
    kwargs = dict(
        test_size=test_size,
        max_test_sets=max_test_sets,
        max_nodes=max_nodes,
        max_class_fraction=max_class_fraction,
    )
    src = aggregate_fullness_relation(group, blocks, source_values, **kwargs)
    dst = aggregate_fullness_relation(group, blocks, target_values, **kwargs)

    if src.status.startswith("undetermined_") or dst.status.startswith("undetermined_"):
        return CanonicalLocalPartitionIsoCoset(
            "undetermined_local_partition", src, dst, None, 0,
            "at least one canonical local-certificate relation exceeded a certified resource bound",
        )

    if src.significant_split != dst.significant_split:
        return CanonicalLocalPartitionIsoCoset(
            "canonical_partition_invariant_mismatch", src, dst, None, 0,
            "isomorphic inputs must agree on whether the canonical construction yields a significant split",
        )

    if not src.significant_split:
        return CanonicalLocalPartitionIsoCoset(
            "canonical_partition_no_progress", src, dst, None, 0,
            "both canonical relations are valid but neither supplies the significant partition required by this recurrence branch",
        )

    src_sizes = tuple(len(c) for c in src.color_classes)
    dst_sizes = tuple(len(c) for c in dst.color_classes)
    if src_sizes != dst_sizes:
        return CanonicalLocalPartitionIsoCoset(
            "canonical_partition_invariant_mismatch", src, dst, None, 0,
            "ordered canonical color-class sizes differ",
        )

    transport = canonical_partition_transporter(
        group,
        blocks,
        src.color_classes,
        dst.color_classes,
        max_states=max_partition_states,
    )
    if transport.status == "undetermined_partition_orbit_limit":
        return CanonicalLocalPartitionIsoCoset(
            transport.status, src, dst, None, transport.orbit_states,
            transport.reason,
        )
    if transport.status != "partition_transporter_coset":
        return CanonicalLocalPartitionIsoCoset(
            "no_partition_respecting_g_candidate", src, dst, None,
            transport.orbit_states,
            "the target canonical partition is not in the source partition's ambient G-orbit",
        )

    target_stabilizer = _target_stabilizer(
        transport.source_stabilizer, transport.transporter
    )
    coset = RightCoset(target_stabilizer, transport.transporter)
    return CanonicalLocalPartitionIsoCoset(
        "canonical_partition_candidate_coset", src, dst, coset,
        transport.orbit_states,
        "exact G-coset of candidates mapping every ordered source canonical color cell to the corresponding target cell",
    )
