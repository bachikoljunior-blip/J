from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log2
from typing import Optional, Tuple


@dataclass(frozen=True)
class RecurrenceChild:
    domain_size: int
    multiplicity: int = 1
    canonical_partition_cells: Tuple[int, ...] = ()


@dataclass(frozen=True)
class RecurrenceCertificate:
    parent_domain_size: int
    children: Tuple[RecurrenceChild, ...]
    progress_kind: str
    local_certificate_count: int
    canonical: bool
    complexity_charge: int
    reason: str


@dataclass(frozen=True)
class RecurrenceValidation:
    status: str
    progress_verified: bool
    charged_log2_work: int
    reason: str


def validate_babai_recurrence_step(
    cert: RecurrenceCertificate,
    *,
    max_branch_factor: Optional[int] = None,
    min_shrink_fraction: float = 0.01,
) -> RecurrenceValidation:
    """Fail-closed structural contract for a future Babai-style recurrence step.

    This does not assert Babai's quasipolynomial theorem. It provides the local
    mechanically checkable obligations that every implemented recurrence step
    must satisfy before the master reducer may claim progress: canonicality,
    positive bounded children, strict measure decrease, bounded branching, and
    an explicit nonnegative accounting charge.
    """
    n = cert.parent_domain_size
    if n <= 1:
        return RecurrenceValidation("invalid_parent", False, 0, "parent domain must exceed one")
    if not cert.canonical:
        return RecurrenceValidation("noncanonical_step", False, 0, "step is not certified label-invariant")
    if cert.local_certificate_count < 0 or cert.complexity_charge < 0:
        return RecurrenceValidation("invalid_accounting", False, 0, "certificate counts and charges must be nonnegative")
    if not cert.children:
        return RecurrenceValidation("no_children", False, 0, "a nonterminal recurrence step must expose children")

    total_mult = 0
    required_shrink = max(1, ceil(n * min_shrink_fraction))
    for child in cert.children:
        if child.multiplicity <= 0 or child.domain_size <= 0:
            return RecurrenceValidation("invalid_child", False, 0, "child size and multiplicity must be positive")
        if child.domain_size > n - required_shrink:
            return RecurrenceValidation("insufficient_progress", False, 0, "every child must strictly reduce the certified domain measure")
        if child.canonical_partition_cells:
            if any(x <= 0 for x in child.canonical_partition_cells):
                return RecurrenceValidation("invalid_partition", False, 0, "partition cells must be positive")
            if sum(child.canonical_partition_cells) != n:
                return RecurrenceValidation("invalid_partition", False, 0, "canonical partition cells must cover the parent domain")
        total_mult += child.multiplicity

    if max_branch_factor is not None and total_mult > max_branch_factor:
        return RecurrenceValidation("branch_limit_exceeded", False, 0, "certified branch multiplicity exceeds the caller budget")

    structural_charge = ceil(log2(max(2, total_mult))) + cert.complexity_charge
    return RecurrenceValidation(
        "verified_local_recurrence_step",
        True,
        structural_charge,
        "canonical children strictly reduce the local domain measure and branching/accounting obligations are explicit",
    )
