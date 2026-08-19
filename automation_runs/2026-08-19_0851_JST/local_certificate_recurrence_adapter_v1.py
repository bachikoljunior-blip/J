from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log2
from typing import Optional

from aggregate_local_certificate_relation import (
    AggregatedCertificateRelation,
    aggregate_fullness_relation,
)
from babai_recurrence_contract_v1 import (
    RecurrenceCertificate,
    RecurrenceChild,
    RecurrenceValidation,
    validate_babai_recurrence_step,
)


@dataclass(frozen=True)
class LocalCertificateRecurrenceResult:
    status: str
    relation: AggregatedCertificateRelation
    certificate: Optional[RecurrenceCertificate]
    validation: Optional[RecurrenceValidation]
    reason: str


def local_certificate_recurrence_step(
    group,
    blocks,
    values,
    *,
    test_size=3,
    max_test_sets=200000,
    max_nodes=500000,
    max_class_fraction=0.9,
    max_branch_factor=None,
) -> LocalCertificateRecurrenceResult:
    """Turn the canonical rev116 local-certificate split into a rev144 step.

    The adapter deliberately does not invent a split.  It reuses the exact
    global fullness/non-fullness relation from rev115-116 and only emits a
    recurrence certificate when canonical incidence refinement already proves a
    significant quotient partition.  The child measure is quotient-cell size;
    the partition signature is sorted by cell size so the accounting payload is
    independent of quotient point names.  No-split and resource-limit outcomes
    remain fail-closed for the later Design/Split-or-Johnson path.
    """
    relation = aggregate_fullness_relation(
        group,
        blocks,
        values,
        test_size=test_size,
        max_test_sets=max_test_sets,
        max_nodes=max_nodes,
        max_class_fraction=max_class_fraction,
    )

    if relation.status.startswith("undetermined_"):
        return LocalCertificateRecurrenceResult(
            relation.status,
            relation,
            None,
            None,
            "local-certificate aggregation exceeded a certified resource bound",
        )

    if not relation.significant_split:
        return LocalCertificateRecurrenceResult(
            "canonical_local_relation_no_recurrence_split",
            relation,
            None,
            None,
            "canonical local-certificate relation exists but does not yet provide a significant split",
        )

    cell_sizes = tuple(sorted(len(cell) for cell in relation.color_classes))
    structural_charge = ceil(log2(max(2, relation.test_count + 1)))
    certificate = RecurrenceCertificate(
        parent_domain_size=relation.quotient_size,
        children=tuple(
            RecurrenceChild(
                domain_size=size,
                multiplicity=1,
                canonical_partition_cells=cell_sizes,
            )
            for size in cell_sizes
        ),
        progress_kind="canonical_local_certificate_partition",
        local_certificate_count=relation.test_count,
        canonical=True,
        complexity_charge=structural_charge,
        reason=(
            "rev115-116 exact fullness/non-fullness relation and canonical incidence "
            "refinement produced the quotient partition"
        ),
    )
    validation = validate_babai_recurrence_step(
        certificate,
        max_branch_factor=(relation.quotient_size if max_branch_factor is None else max_branch_factor),
        min_shrink_fraction=max(0.01, 1.0 - max_class_fraction),
    )
    if not validation.progress_verified:
        return LocalCertificateRecurrenceResult(
            "local_partition_failed_recurrence_contract",
            relation,
            certificate,
            validation,
            "a claimed canonical split failed the independent recurrence obligations",
        )

    return LocalCertificateRecurrenceResult(
        "verified_local_certificate_recurrence_step",
        relation,
        certificate,
        validation,
        "canonical local-certificate partition is connected to a mechanically verified shrinking recurrence step",
    )
