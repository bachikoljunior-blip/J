from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb

from aggregate_local_certificate_relation import (
    AggregatedCertificateRelation,
    _aggregate_boolean_relation,
)
from babai_local_certificate_parameter_gate_v1 import (
    BabaiLocalCertificateParameterGate,
    babai_local_certificate_parameter_gate,
)
from local_certificate_beard_v1 import LocalCertificateBeard, local_certificate_beard


@dataclass(frozen=True)
class TheoremLocalCertificateRelation:
    status: str
    quotient_size: int
    test_size: int
    test_count: int
    certificates_checked: int
    full_count: int
    nonfull_count: int
    undetermined_count: int
    parameter_gate: BabaiLocalCertificateParameterGate
    certificates: tuple[LocalCertificateBeard, ...]
    aggregate: AggregatedCertificateRelation | None
    local_certificates_complete: bool
    theorem_scale_complete: bool
    exact: bool
    reason: str


def aggregate_beard_local_certificate_relation(
    group,
    blocks,
    values,
    *,
    test_size: int,
    max_test_sets: int = 200000,
    max_class_fraction: float = 0.9,
    max_layers: int | None = None,
    max_quotient_leaves: int = 2000000,
    max_child_nodes: int = 200000,
    max_preimage_schreier_work: int = 1000000000,
    max_giant_action_schreier_work: int = 1000000000,
    require_theorem_scale: bool = True,
) -> TheoremLocalCertificateRelation:
    """Build a complete Boolean t-subset relation from growing-beard proofs.

    This path never computes the global string stabilizer.  Every Boolean entry
    must be returned by the actual local-certificate execution for that test set.
    An unknown entry withholds the complete relation.  Theorem mode additionally
    requires the primary parameter window and theorem-scale recurrence evidence
    on every local certificate.

    ``require_theorem_scale=False`` only exposes exact bounded evidence for
    regression and composition work.  Such output remains explicitly labelled
    as non-theorem-scale and cannot discharge the CRX2 parent.
    """
    blocks = tuple(tuple(block) for block in blocks)
    vals = tuple(values)
    m = len(blocks)
    t = int(test_size)
    if len(vals) != group.degree:
        raise ValueError("string/domain size mismatch")
    if t < 5 or t > m:
        raise ValueError("growing-beard test_size must lie in [5,m]")
    if not 0 < max_class_fraction < 1:
        raise ValueError("max_class_fraction must lie in (0,1)")
    if max_test_sets < 1:
        raise ValueError("max_test_sets must be positive")

    total = comb(m, t)
    gate = babai_local_certificate_parameter_gate(group.degree, m, t)
    if total > max_test_sets:
        return TheoremLocalCertificateRelation(
            "undetermined_testset_limit", m, t, total, 0, 0, 0, total,
            gate, (), None, False, False, False,
            "complete local-certificate relation exceeds max_test_sets before any certificate execution",
        )
    if require_theorem_scale and not gate.certified:
        return TheoremLocalCertificateRelation(
            "undetermined_theorem_parameter_window", m, t, total, 0, 0, 0,
            total, gate, (), None, False, False, False,
            "Babai local-certificate parameter window is unavailable; bounded exactness is not promoted to theorem-scale aggregation",
        )

    certificates = []
    relation = []
    full_count = 0
    nonfull_count = 0
    theorem_complete = bool(gate.certified)
    for T in combinations(range(m), t):
        cert = local_certificate_beard(
            group,
            blocks,
            vals,
            T,
            max_layers=max_layers,
            max_quotient_leaves=max_quotient_leaves,
            max_child_nodes=max_child_nodes,
            max_preimage_schreier_work=(
                max_preimage_schreier_work if require_theorem_scale else None
            ),
            max_giant_action_schreier_work=(
                max_giant_action_schreier_work if require_theorem_scale else None
            ),
        )
        certificates.append(cert)
        if cert.full is None:
            remaining = total - len(certificates)
            return TheoremLocalCertificateRelation(
                "undetermined_local_certificate", m, t, total,
                len(certificates), full_count, nonfull_count, remaining + 1,
                gate, tuple(certificates), None, False, False, False,
                "at least one growing-beard execution returned no exact Boolean; the complete relation is withheld",
            )
        full = bool(cert.full)
        relation.append((T, full))
        full_count += int(full)
        nonfull_count += int(not full)
        theorem_complete = theorem_complete and cert.theorem_scale_recurrence_evidence
        if require_theorem_scale and not cert.theorem_scale_recurrence_evidence:
            remaining = total - len(certificates)
            return TheoremLocalCertificateRelation(
                "undetermined_theorem_scale_local_evidence", m, t, total,
                len(certificates), full_count, nonfull_count, remaining,
                gate, tuple(certificates), None, False, False, False,
                "an exact local Boolean lacks the theorem-scale recurrence envelope; aggregation remains fail closed",
            )

    aggregate = _aggregate_boolean_relation(
        m,
        t,
        relation,
        max_class_fraction=max_class_fraction,
        reason="complete growing-beard local-certificate relation plus canonical colored-incidence refinement",
    )
    theorem_scale = bool(theorem_complete and len(certificates) == total)
    return TheoremLocalCertificateRelation(
        (
            "certified_theorem_local_certificate_relation"
            if theorem_scale
            else "bounded_exact_beard_relation_without_theorem_scale"
        ),
        m, t, total, len(certificates), full_count, nonfull_count, 0,
        gate, tuple(certificates), aggregate, True, theorem_scale, True,
        (
            "every t-subset Boolean was produced by its own growing-beard proof and aggregated canonically"
            + (" with theorem-scale evidence" if theorem_scale else "; the bounded exact relation is not theorem-scale evidence")
        ),
    )


__all__ = [
    "TheoremLocalCertificateRelation",
    "aggregate_beard_local_certificate_relation",
]
