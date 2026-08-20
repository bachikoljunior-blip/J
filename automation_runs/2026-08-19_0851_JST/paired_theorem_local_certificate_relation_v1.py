from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from theorem_local_certificate_relation_v1 import TheoremLocalCertificateRelation


@dataclass(frozen=True)
class PairedTheoremLocalCertificateRelation:
    status: str
    source: TheoremLocalCertificateRelation
    target: TheoremLocalCertificateRelation
    source_palette: tuple[bool, ...]
    target_palette: tuple[bool, ...]
    canonical_test_order_certified: bool
    necessary_palette_invariants_match: bool
    exact_empty: bool
    ready_for_relation_si: bool
    reason: str


def _complete_theorem_palette(relation: TheoremLocalCertificateRelation):
    aggregate = relation.aggregate
    envelope = relation.all_test_resource_envelope
    if (
        not relation.exact
        or not relation.local_certificates_complete
        or not relation.theorem_scale_complete
        or not relation.parameter_gate.certified
        or aggregate is None
        or envelope is None
        or not envelope.admitted
        or not envelope.complete
        or envelope.executed_test_count != relation.test_count
        or envelope.unexecuted_test_count != 0
        or relation.certificates_checked != relation.test_count
        or relation.undetermined_count != 0
    ):
        return None
    expected = tuple(combinations(range(relation.quotient_size), relation.test_size))
    relation_coordinates = tuple(T for T, _ in aggregate.relation)
    certificate_coordinates = tuple(tuple(cert.test_set) for cert in relation.certificates)
    if (
        relation.test_count != len(expected)
        or aggregate.test_count != len(expected)
        or relation_coordinates != expected
        or certificate_coordinates != expected
    ):
        return None
    return tuple(bool(full) for _, full in aggregate.relation)


def pair_theorem_local_certificate_relations(
    source: TheoremLocalCertificateRelation,
    target: TheoremLocalCertificateRelation,
) -> PairedTheoremLocalCertificateRelation:
    """Pair two complete all-T artifacts without choosing point labels.

    A palette histogram mismatch is an exact necessary-invariant failure under
    every quotient permutation.  A matching histogram is only an admissible
    relation-SI input; it is not itself an isomorphism or a Design conclusion.
    Unknown, incomplete, out-of-order, or unreserved evidence stays fail closed.
    """
    metadata = (
        source.quotient_size,
        source.test_size,
        source.test_count,
    )
    if metadata != (
        target.quotient_size,
        target.test_size,
        target.test_count,
    ):
        return PairedTheoremLocalCertificateRelation(
            "incompatible_relation_metadata", source, target, (), (), False,
            False, False, False,
            "source and target do not describe the same t-subset ground",
        )

    source_palette = _complete_theorem_palette(source)
    target_palette = _complete_theorem_palette(target)
    if source_palette is None or target_palette is None:
        return PairedTheoremLocalCertificateRelation(
            "undetermined_incomplete_paired_evidence", source, target,
            source_palette or (), target_palette or (), False, False, False,
            False,
            "both sides must carry complete canonical all-T theorem evidence and a completed finite reservation",
        )

    matched = Counter(source_palette) == Counter(target_palette)
    return PairedTheoremLocalCertificateRelation(
        (
            "paired_relation_palette_mismatch_exact_empty"
            if not matched else "certified_paired_relation_si_input"
        ),
        source,
        target,
        source_palette,
        target_palette,
        True,
        matched,
        not matched,
        matched,
        (
            "Boolean palette multiplicities differ, so no quotient permutation can transport the complete relation"
            if not matched else
            "both complete relations are canonically ordered and pass necessary palette invariants; exact relation SI remains downstream"
        ),
    )


__all__ = [
    "PairedTheoremLocalCertificateRelation",
    "pair_theorem_local_certificate_relations",
]
