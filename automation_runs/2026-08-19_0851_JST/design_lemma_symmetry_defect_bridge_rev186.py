from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Hashable, Iterable

from colored_subset_symmetry_defect_v1 import (
    SymmetryDefectCertificate,
    exact_colored_subset_symmetry_defect,
)


@dataclass(frozen=True)
class PairedDesignDefectBridge:
    status: str
    source: SymmetryDefectCertificate
    target: SymmetryDefectCertificate
    exact: bool
    theorem_hypothesis_certified: bool
    reason: str


def paired_design_symmetry_defect_bridge(
    vertex_count: int,
    arity: int,
    source_colors: Iterable[Hashable],
    target_colors: Iterable[Hashable],
    *,
    alpha: float = 0.9,
) -> PairedDesignDefectBridge:
    """Exact paired gate for rev184's codegree-homogeneous Design-Lemma leaf.

    This bridge deliberately certifies only the symmetry-defect hypothesis.  It
    does not claim the Design Lemma conclusion, a canonical split, Johnson
    reduction, full W1R-H5 closure, or AGI.  Source/target color multiplicities
    and exact twin-class size profiles are compared before the theorem gate is
    exposed to later proof-carrying descent.
    """
    source_colors = tuple(source_colors)
    target_colors = tuple(target_colors)
    src = exact_colored_subset_symmetry_defect(
        vertex_count, arity, source_colors, alpha=alpha
    )
    dst = exact_colored_subset_symmetry_defect(
        vertex_count, arity, target_colors, alpha=alpha
    )

    if Counter(source_colors) != Counter(target_colors):
        return PairedDesignDefectBridge(
            "relation_invariant_mismatch", src, dst, True, False,
            "source/target colored relation multiplicities differ",
        )

    src_profile = tuple(sorted(map(len, src.twin_classes)))
    dst_profile = tuple(sorted(map(len, dst.twin_classes)))
    if src_profile != dst_profile:
        return PairedDesignDefectBridge(
            "symmetry_defect_invariant_mismatch", src, dst, True, False,
            "exact largest-symmetric-subset profiles differ",
        )

    gate = src.design_gate_certified and dst.design_gate_certified
    if gate:
        return PairedDesignDefectBridge(
            "design_lemma_symmetry_defect_hypothesis_certified",
            src, dst, True, True,
            "both colored relations satisfy the exact symmetry-defect hypothesis; theorem conclusion remains a separate proof obligation",
        )

    return PairedDesignDefectBridge(
        "design_lemma_symmetry_defect_hypothesis_not_certified",
        src, dst, True, False,
        "at least one relation has a symmetric subset larger than the configured alpha fraction",
    )
