from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from aggregate_local_certificate_relation import aggregate_fullness_relation
from canonical_no_split_obstruction import classify_no_split_obstruction
from pair_codegree_canonical_refinement import refine_pair_codegrees
from johnson_pair_relation_recognizer import recognize_johnson_pair_relation


@dataclass(frozen=True)
class CanonicalPartitionPipelineResult:
    status: str
    quotient_size: int
    split_classes: Tuple[Tuple[int, ...], ...]
    giant_type: Optional[str]
    johnson_ground_size: Optional[int]
    johnson_subset_size: Optional[int]
    decisive_relation_level: str
    reason: str


def canonical_partition_pipeline(
    group,
    blocks,
    values,
    *,
    max_nodes=500000,
    max_test_sets=200000,
    max_class_fraction=0.9,
    max_johnson_nodes=500000,
) -> CanonicalPartitionPipelineResult:
    """Fail-closed split/giant/Johnson classifier for the current quotient leaf.

    The stages are all canonical with respect to quotient renumbering:
      1. exact local-certificate aggregation and incidence refinement (rev116),
      2. exact uniformly-full A_m/S_m obstruction certificate (rev117),
      3. pair-codegree refinement (rev118),
      4. bounded exact Johnson recognition of each pair-weight color (rev119).

    No unresolved homogeneous/non-Johnson relation is relabeled as a Johnson
    obstruction. The result exposes exactly which structural level succeeded so
    the master recurrence can choose the corresponding child problem.
    """
    blocks = tuple(tuple(b) for b in blocks)
    m = len(blocks)
    agg = aggregate_fullness_relation(
        group, blocks, values,
        test_size=3,
        max_test_sets=max_test_sets,
        max_nodes=max_nodes,
        max_class_fraction=max_class_fraction,
    )
    if agg.status in {"undetermined_testset_limit", "undetermined_search_limit"}:
        return CanonicalPartitionPipelineResult(
            agg.status, m, (), None, None, None, "local_certificate_aggregation", agg.reason,
        )
    if agg.significant_split:
        return CanonicalPartitionPipelineResult(
            "certified_significant_split", m, agg.color_classes, None, None, None,
            "local_certificate_incidence",
            "rev116 local-certificate incidence refinement produced a significant canonical partition",
        )

    obstruction = classify_no_split_obstruction(
        group, blocks, values,
        test_size=3,
        max_test_sets=max_test_sets,
        max_nodes=max_nodes,
        max_class_fraction=max_class_fraction,
    )
    if obstruction.status == "certified_global_alternating_obstruction":
        return CanonicalPartitionPipelineResult(
            "certified_global_alternating_obstruction", m, obstruction.split_classes,
            obstruction.giant_type, None, None, "global_alternating_image", obstruction.reason,
        )
    if obstruction.status.startswith("undetermined"):
        return CanonicalPartitionPipelineResult(
            obstruction.status, m, obstruction.split_classes, None, None, None,
            "global_alternating_image", obstruction.reason,
        )

    pair = refine_pair_codegrees(m, agg.relation, max_class_fraction=max_class_fraction)
    if pair.significant_split:
        return CanonicalPartitionPipelineResult(
            "certified_pair_codegree_split", m, pair.color_classes, None, None, None,
            "pair_codegree", pair.reason,
        )
    if pair.status == "canonical_edge_colored_relation":
        johnson = recognize_johnson_pair_relation(
            m, pair.pair_weights, max_nodes_per_candidate=max_johnson_nodes
        )
        if johnson.status == "exact_johnson_color_relation":
            return CanonicalPartitionPipelineResult(
                "exact_johnson_obstruction", m, pair.color_classes, None,
                johnson.ground_size, johnson.subset_size, "pair_weight_johnson", johnson.reason,
            )
        if johnson.status == "undetermined_search_limit":
            return CanonicalPartitionPipelineResult(
                "undetermined_johnson_search_limit", m, pair.color_classes, None,
                None, None, "pair_weight_johnson", johnson.reason,
            )
        return CanonicalPartitionPipelineResult(
            "canonical_nonjohnson_pair_relation", m, pair.color_classes, None,
            None, None, "pair_weight_relation",
            "nonconstant canonical pair relation exists, but no pair-weight color was exactly Johnson; stronger coherent/design reduction is required",
        )

    return CanonicalPartitionPipelineResult(
        "homogeneous_pair_obstruction", m, pair.color_classes, None, None, None,
        "pair_codegree_homogeneous",
        "local-certificate relation remains homogeneous through pair codegrees; higher-arity Design-Lemma-style reduction is required",
    )
