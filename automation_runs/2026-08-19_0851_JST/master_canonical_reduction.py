from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Optional, Tuple

from aggregate_local_certificate_relation import aggregate_fullness_relation
from pair_codegree_canonical_refinement import refine_pair_codegrees
from coherent_pair_refinement import coherent_refine_pair_relation
from johnson_pair_relation_recognizer import recognize_johnson_pair_relation
from johnson_coherent_scheme_certificate import certify_johnson_coherent_scheme
from giant_parity_reduction import reduce_global_giant_to_parity_classes
from design_codegree_refinement import refine_design_codegrees


@dataclass(frozen=True)
class CanonicalReductionResult:
    status: str
    original_domain_size: int
    reduced_domain_size: Optional[int]
    branch_count: int
    split_classes: Tuple[Tuple[int, ...], ...]
    johnson_ground_size: Optional[int]
    johnson_subset_size: Optional[int]
    giant_type: Optional[str]
    progress_kind: str
    progress_verified: bool
    reason: str


def reduce_canonical_pair_structure(
    quotient_size: int,
    pair_weights,
    *,
    max_class_fraction=0.9,
    max_johnson_nodes=500000,
) -> CanonicalReductionResult:
    """Reduce an already canonical pair relation via coherent/Johnson structure."""
    m = int(quotient_size)
    coherent = coherent_refine_pair_relation(
        m, pair_weights, max_class_fraction=max_class_fraction
    )
    if coherent.status == "undetermined_round_limit":
        return CanonicalReductionResult(
            coherent.status, m, None, 0, (), None, None, None,
            "none", False, coherent.reason,
        )
    if coherent.significant_split:
        largest = coherent.largest_class
        return CanonicalReductionResult(
            "certified_coherent_point_split", m, largest, len(coherent.color_classes),
            coherent.color_classes, None, None, None,
            "domain_split", largest < m,
            "stable coherent pair refinement yields a canonical point partition",
        )

    johnson = recognize_johnson_pair_relation(
        m, pair_weights, max_nodes_per_candidate=max_johnson_nodes
    )
    if johnson.status == "undetermined_search_limit":
        return CanonicalReductionResult(
            "undetermined_johnson_search_limit", m, None, 0, coherent.color_classes,
            None, None, None, "none", False, johnson.reason,
        )
    if johnson.status == "exact_johnson_color_relation":
        scheme = certify_johnson_coherent_scheme(coherent, johnson)
        if scheme.exact_distance_scheme:
            v = int(johnson.ground_size)
            k = int(johnson.subset_size)
            # For 2<=k<=v/2, C(v,k)>=C(v,2), so this check records the
            # strong square-root-scale domain reduction numerically.
            upper = (1.0 + sqrt(1.0 + 8.0 * m)) / 2.0
            strong = v <= upper + 1e-12 and v < m
            return CanonicalReductionResult(
                "exact_johnson_ground_reduction_available", m, v, 1,
                coherent.color_classes, v, k, None,
                "johnson_ground_domain", strong,
                "the full coherent pair relation is exactly the Johnson distance scheme; quotient vertices reduce to k-subsets of a smaller v-point ground domain",
            )
        return CanonicalReductionResult(
            "johnson_graph_with_refined_coherent_structure", m, None, 0,
            coherent.color_classes, johnson.ground_size, johnson.subset_size, None,
            "none", False,
            "a Johnson graph color is present, but additional coherent colors refine the Johnson scheme; full coordinate ambiguity must be intersected before ground reduction",
        )

    return CanonicalReductionResult(
        "stable_nonjohnson_coherent_relation", m, None, 0, coherent.color_classes,
        None, None, None, "none", False,
        "stable homogeneous coherent pair relation is not exactly Johnson at any pair-weight color; higher-arity/design recursion remains",
    )


def master_canonical_reduction(
    group,
    blocks,
    values,
    *,
    max_nodes=500000,
    max_test_sets=200000,
    max_class_fraction=0.9,
    max_johnson_nodes=500000,
) -> CanonicalReductionResult:
    """Execute the implemented canonical reduction branches without overclaiming.

    The result is one of: a significant domain split, a constant-size parity
    reduction for an A_m/S_m quotient, an exact Johnson ground-domain reduction,
    or an explicitly unresolved coherent/design obstruction. This is a verified
    reduction layer for the master recurrence, not yet a proof that every input
    reaches a quasipolynomial terminal case.
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
        return CanonicalReductionResult(
            agg.status, m, None, 0, (), None, None, None,
            "none", False, agg.reason,
        )
    if agg.significant_split:
        largest = agg.largest_class
        return CanonicalReductionResult(
            "certified_local_certificate_split", m, largest, len(agg.color_classes),
            agg.color_classes, None, None, None,
            "domain_split", largest < m,
            "local-certificate incidence aggregation yields a canonical significant split",
        )

    if agg.nonfull_count == 0:
        giant = reduce_global_giant_to_parity_classes(
            group, blocks, values, max_nodes=max_nodes
        )
        if giant.status in {"symmetric_single_quotient_orbit", "alternating_two_parity_classes"}:
            return CanonicalReductionResult(
                "exact_giant_parity_reduction", m, m, giant.parity_branch_count,
                agg.color_classes, None, None, giant.giant_type,
                "constant_parity_branching", giant.parity_branch_count <= 2,
                giant.reason,
            )
        return CanonicalReductionResult(
            giant.status, m, None, 0, agg.color_classes, None, None, None,
            "none", False, giant.reason,
        )

    pair = refine_pair_codegrees(m, agg.relation, max_class_fraction=max_class_fraction)
    if pair.significant_split:
        largest = pair.largest_class
        return CanonicalReductionResult(
            "certified_pair_codegree_split", m, largest, len(pair.color_classes),
            pair.color_classes, None, None, None,
            "domain_split", largest < m, pair.reason,
        )

    pair_stage = reduce_canonical_pair_structure(
        m, pair.pair_weights,
        max_class_fraction=max_class_fraction,
        max_johnson_nodes=max_johnson_nodes,
    )
    if pair_stage.progress_verified or pair_stage.status.startswith("undetermined"):
        return pair_stage

    # Preserve the exact higher-arity obstruction as a final fail-closed attempt
    # before returning unresolved.
    design = refine_design_codegrees(
        m, tuple((T, int(full)) for T, full in agg.relation),
        max_class_fraction=max_class_fraction,
    )
    if design.significant_split:
        largest = design.largest_class
        return CanonicalReductionResult(
            "certified_design_codegree_split", m, largest, len(design.color_classes),
            design.color_classes, None, None, None,
            "domain_split", largest < m, design.reason,
        )
    return CanonicalReductionResult(
        "unresolved_homogeneous_design_or_coherent_obstruction", m, None, 0,
        design.color_classes, None, None, None,
        "none", False,
        "all implemented canonical split/giant/Johnson reductions exhausted; the remaining homogeneous design/coherent case is preserved as the next unsolved leaf",
    )
