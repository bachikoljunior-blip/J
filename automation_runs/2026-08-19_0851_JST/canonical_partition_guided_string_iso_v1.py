from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional, Tuple

from babai_recurrence_contract_v1 import RecurrenceValidation
from canonical_local_partition_iso_coset_v1 import (
    CanonicalLocalPartitionIsoCoset,
    canonical_local_partition_iso_coset,
)
from coset_stabilizer_primitives import RightCoset
from local_fullness_certificates import _young_group
from permutation_group_schreier import Permutation
from recursive_point_image_coset_intersection import (
    RecursiveCosetIntersection,
    right_coset_intersection_recursive,
)


@dataclass(frozen=True)
class CanonicalPartitionGuidedStringIso:
    status: str
    partition_stage: CanonicalLocalPartitionIsoCoset
    exact_intersection: Optional[RecursiveCosetIntersection]
    isomorphism_coset: Optional[RightCoset]
    child_measure: Optional[int]
    progress_verified: bool
    reason: str


def _value_mapping_representative(source_values, target_values) -> Optional[Permutation]:
    src = tuple(source_values)
    dst = tuple(target_values)
    if len(src) != len(dst):
        return None
    try:
        if Counter(src) != Counter(dst):
            return None
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc

    dst_positions = {}
    for j, value in enumerate(dst):
        dst_positions.setdefault(value, []).append(j)
    used = {value: 0 for value in dst_positions}
    p = [None] * len(src)
    for i, value in enumerate(src):
        k = used[value]
        p[i] = dst_positions[value][k]
        used[value] = k + 1
    return tuple(p)


def _all_value_preserving_maps(source_values, target_values) -> Optional[RightCoset]:
    representative = _value_mapping_representative(source_values, target_values)
    if representative is None:
        return None
    # The target Young subgroup preserves each target value class.  Left
    # composition after `representative` gives every source->target value map,
    # matching RightCoset.contains' convention in this repository.
    target_young = _young_group(tuple(target_values))
    return RightCoset(target_young, representative)


def canonical_partition_guided_string_iso(
    group,
    blocks,
    source_values,
    target_values,
    *,
    test_size=3,
    max_test_sets=200000,
    max_local_nodes=500000,
    max_class_fraction=0.9,
    max_partition_states=200000,
    max_intersection_nodes=500000,
) -> CanonicalPartitionGuidedStringIso:
    """Exact string-isomorphism coset after a verified canonical split.

    The rev147 partition stage returns the exact subset of G mapping source
    canonical cells to target canonical cells.  Independently, a Young-group
    coset represents all permutations mapping source values to target values.
    Their exact resource-bounded intersection is therefore precisely the G-string
    isomorphisms, provided this canonical split branch is available.  Any true
    isomorphism must transport the canonical relation/partition, so this filter
    cannot remove a true isomorphism when the preceding certificates are valid.

    This is correctness plumbing, not a quasipolynomial complexity claim: the
    local relation, partition orbit, and exact coset intersection are all bounded
    and fail closed when their current exact implementations exhaust resources.
    """
    partition = canonical_local_partition_iso_coset(
        group,
        blocks,
        source_values,
        target_values,
        test_size=test_size,
        max_test_sets=max_test_sets,
        max_nodes=max_local_nodes,
        max_class_fraction=max_class_fraction,
        max_partition_states=max_partition_states,
    )

    if partition.status == "canonical_partition_invariant_mismatch":
        return CanonicalPartitionGuidedStringIso(
            "non_isomorphic_by_canonical_partition", partition, None, None,
            None, True,
            "canonical partition invariant mismatch proves no ambient G string isomorphism",
        )
    if partition.status in {
        "undetermined_local_partition",
        "undetermined_partition_orbit_limit",
    }:
        return CanonicalPartitionGuidedStringIso(
            partition.status, partition, None, None, None, False,
            "canonical partition stage exhausted a certified resource bound",
        )
    if partition.status == "canonical_partition_no_progress":
        return CanonicalPartitionGuidedStringIso(
            "canonical_partition_no_progress", partition, None, None,
            None, False,
            "valid canonical relation exists but this split recurrence branch has no strict child measure reduction",
        )
    if partition.status == "no_partition_respecting_g_candidate":
        return CanonicalPartitionGuidedStringIso(
            "non_isomorphic_by_partition_orbit", partition, None, None,
            None, True,
            "no element of G transports the source canonical partition to the target partition",
        )
    if partition.status != "canonical_partition_candidate_coset":
        return CanonicalPartitionGuidedStringIso(
            "undetermined_partition_stage", partition, None, None,
            None, False,
            "unexpected partition-stage status; fail closed",
        )

    value_coset = _all_value_preserving_maps(source_values, target_values)
    if value_coset is None:
        return CanonicalPartitionGuidedStringIso(
            "non_isomorphic_value_multiplicity", partition, None, None,
            None, True,
            "source and target strings have different value multiplicities",
        )

    intersection = right_coset_intersection_recursive(
        partition.candidate_coset,
        value_coset,
        max_nodes=max_intersection_nodes,
    )
    if intersection.status == "undetermined_node_limit":
        return CanonicalPartitionGuidedStringIso(
            "undetermined_intersection_limit", partition, intersection, None,
            None, False,
            "exact partition/value coset intersection exceeded max_intersection_nodes",
        )
    if intersection.status == "empty_intersection":
        return CanonicalPartitionGuidedStringIso(
            "non_isomorphic_exact_partition_intersection", partition,
            intersection, None, 0, True,
            "exact candidate intersection is empty",
        )

    if intersection.status != "exact_intersection_coset" or intersection.coset is None:
        return CanonicalPartitionGuidedStringIso(
            "undetermined_intersection_status", partition, intersection, None,
            None, False,
            "unexpected exact-intersection status; fail closed",
        )

    largest = max(map(len, partition.target_relation.color_classes))
    if largest >= partition.target_relation.quotient_size:
        return CanonicalPartitionGuidedStringIso(
            "invalid_nonshrinking_partition", partition, intersection, None,
            largest, False,
            "candidate coset exists but the certified quotient measure did not strictly shrink",
        )

    return CanonicalPartitionGuidedStringIso(
        "exact_partition_guided_isomorphism_coset",
        partition,
        intersection,
        intersection.coset,
        largest,
        True,
        "exact partition-respecting G candidates intersected with all source-to-target value-preserving permutations; quotient child measure strictly shrinks",
    )
