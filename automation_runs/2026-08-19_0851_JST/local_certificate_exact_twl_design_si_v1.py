from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from aggregate_local_certificate_relation import (
    AggregatedCertificateRelation,
    aggregate_fullness_relation,
)
from design_lemma_exact_twl_candidate_si_v1 import (
    ExactTWLDesignCandidateSI,
    exact_twl_design_candidate_string_isomorphism,
)
from giant_block_action_certificates import _block_action
from permutation_group_schreier import identity


@dataclass(frozen=True)
class LocalCertificateExactTWLDesignSI:
    status: str
    source_relation: AggregatedCertificateRelation
    target_relation: AggregatedCertificateRelation
    design_result: ExactTWLDesignCandidateSI | None
    relation_order_certified: bool
    exact: bool
    complete: bool
    reason: str


def _complete_boolean_palette(relation: AggregatedCertificateRelation):
    expected = tuple(combinations(range(relation.quotient_size), relation.test_size))
    coordinates = tuple(T for T, _ in relation.relation)
    if coordinates != expected or relation.test_count != len(expected):
        return None
    return tuple(bool(full) for _, full in relation.relation)


def local_certificate_exact_twl_design_string_isomorphism(
    group,
    blocks,
    source_values,
    target_values,
    *,
    root_n: int,
    test_size: int = 3,
    max_test_sets: int = 200000,
    max_nodes: int = 500000,
    max_class_fraction: float = 0.9,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_twl_rounds: int | None = None,
    max_twl_work_units: int = 500000000,
    max_paired_twl_work_units: int = 10**30,
    max_branch_pairs: int = 200000,
    max_partition_states: int = 200000,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
) -> LocalCertificateExactTWLDesignSI:
    """Connect an exact local-certificate relation to exact k-WL Design SI.

    The source and target relations are recomputed from their full strings.  Their
    Boolean colors are accepted only in the complete lexicographic t-subset order
    consumed by standard correlated-replacement t-WL.  Every original generator
    is paired with its induced block action, so Design tuple transport returns an
    original-domain candidate coset and the downstream solver intersects every
    branch with the original full strings.

    This adapter deliberately does not upgrade the current global exact
    string-stabilizer aggregation to Babai's theorem-scale local-certificate
    comparison.  Resource caps, an upstream split, a failed symmetry/parameter
    gate, or an incomplete Design branch remain fail closed.
    """
    blocks = tuple(tuple(block) for block in blocks)
    kwargs = dict(
        test_size=test_size,
        max_test_sets=max_test_sets,
        max_nodes=max_nodes,
        max_class_fraction=max_class_fraction,
    )
    source = aggregate_fullness_relation(group, blocks, source_values, **kwargs)
    target = aggregate_fullness_relation(group, blocks, target_values, **kwargs)

    if source.status.startswith("undetermined_") or target.status.startswith("undetermined_"):
        return LocalCertificateExactTWLDesignSI(
            "undetermined_local_certificate_relation",
            source,
            target,
            None,
            False,
            False,
            False,
            "at least one exact local-certificate aggregation exceeded a configured resource cap",
        )

    if (
        source.quotient_size != len(blocks)
        or target.quotient_size != len(blocks)
        or source.test_size != target.test_size
    ):
        return LocalCertificateExactTWLDesignSI(
            "invalid_local_certificate_relation_metadata",
            source,
            target,
            None,
            False,
            False,
            False,
            "the two aggregate artifacts do not describe the requested common block ground",
        )

    source_palette = _complete_boolean_palette(source)
    target_palette = _complete_boolean_palette(target)
    if source_palette is None or target_palette is None:
        return LocalCertificateExactTWLDesignSI(
            "invalid_local_certificate_relation_order",
            source,
            target,
            None,
            False,
            False,
            False,
            "Design escalation requires every t-subset exactly once in canonical lexicographic order",
        )

    if source.significant_split or target.significant_split:
        return LocalCertificateExactTWLDesignSI(
            "local_certificate_split_precedes_design",
            source,
            target,
            None,
            True,
            False,
            False,
            "at least one side already has the canonical significant split handled by the existing partition recurrence",
        )

    point_to_block = {
        point: block_index
        for block_index, block in enumerate(blocks)
        for point in block
    }
    domain_generators = tuple(group.original_generators) or (identity(group.degree),)
    lifted_generators = tuple(
        (_block_action(generator, blocks, point_to_block), False)
        for generator in domain_generators
    )
    design = exact_twl_design_candidate_string_isomorphism(
        group,
        lifted_generators,
        len(blocks),
        source.test_size,
        source_palette,
        target_palette,
        source_values,
        target_values,
        root_n=root_n,
        alpha=max_class_fraction,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_twl_rounds=max_twl_rounds,
        max_twl_work_units=max_twl_work_units,
        max_paired_twl_work_units=max_paired_twl_work_units,
        max_branch_pairs=max_branch_pairs,
        max_partition_states=max_partition_states,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
    )
    return LocalCertificateExactTWLDesignSI(
        "local_certificate_" + design.status,
        source,
        target,
        design,
        True,
        bool(design.exact),
        bool(design.complete),
        (
            "the complete exact local-certificate relation was transported through standard t-WL, "
            "theorem-gated Design branching, original-domain tuple transport, and full-string SI; "
            + design.reason
        ),
    )


__all__ = [
    "LocalCertificateExactTWLDesignSI",
    "local_certificate_exact_twl_design_string_isomorphism",
]
