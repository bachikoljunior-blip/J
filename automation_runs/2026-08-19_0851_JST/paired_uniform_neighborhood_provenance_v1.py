from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Hashable, Iterable

from bipartite_degree_alpha_partition_v1 import BipartiteDegreePartition, bipartite_degree_alpha_partition
from uniform_neighborhood_hypergraph_v1 import UniformNeighborhoodHypergraph, build_uniform_neighborhood_hypergraph


@dataclass(frozen=True)
class PairedUniformNeighborhoodProvenance:
    status: str
    left_size: int
    right_size: int
    alpha: float
    source_degree_stage: BipartiteDegreePartition
    target_degree_stage: BipartiteDegreePartition
    source_hypergraph: UniformNeighborhoodHypergraph | None
    target_hypergraph: UniformNeighborhoodHypergraph | None
    normalized_degree: int | None
    complemented: bool | None
    selected_left_count: int
    test_arity: int | None
    source_coordinates: tuple[tuple[int, ...], ...]
    source_colors: tuple[int, ...]
    target_coordinates: tuple[tuple[int, ...], ...]
    target_colors: tuple[int, ...]
    relation_color_multiplicity_compatible: bool
    derived_relation_certified: bool
    paired_johnson_certified: bool
    exact_empty: bool
    exact: bool
    reason: str


def _degree_inventory(stage: BipartiteDegreePartition):
    return tuple(
        sorted(
            ((repr(signature), len(cell)) for signature, cell in zip(stage.cell_signatures, stage.color_cells)),
            key=repr,
        )
    )


def certify_paired_uniform_neighborhood_provenance(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 2 / 3,
    source_left_colors: Iterable[Hashable] | None = None,
    target_left_colors: Iterable[Hashable] | None = None,
) -> PairedUniformNeighborhoodProvenance:
    """Mechanically derive comparable rev204 V2 relations from two bipartite states.

    The construction follows the already-audited rev202->rev204 path on both sides:
    canonical left color/degree refinement, the unique alpha-dominant same-degree
    twin-free cell, common-degree neighborhood hypergraphs on V2, optional global
    bipartite complementation, then either the complete-uniform Johnson case or the
    exact containment-count test relation.

    Every operation is defined directly from the colored bipartite incidence
    relation and commutes with color-preserving relabeling of the two parts. Thus an
    isomorphism of the input bipartite states necessarily transports the produced V2
    colored-subset relation. This object certifies that *bipartite-subproblem*
    provenance; a caller working inside a larger string/group reduction must still
    prove that its bipartite state itself was derived equivariantly from that larger
    parent before promoting the relation to the parent's complete isomorphism set.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 1 or n2 < 2:
        raise ValueError("paired uniform-neighborhood provenance requires positive left_size and right_size>=2")

    source_degree = bipartite_degree_alpha_partition(
        n1, n2, source_edges, alpha=alpha, left_colors=source_left_colors
    )
    target_degree = bipartite_degree_alpha_partition(
        n1, n2, target_edges, alpha=alpha, left_colors=target_left_colors
    )

    if _degree_inventory(source_degree) != _degree_inventory(target_degree):
        return PairedUniformNeighborhoodProvenance(
            "exact_empty_bipartite_degree_inventory",
            n1, n2, float(alpha), source_degree, target_degree, None, None,
            None, None, 0, None, (), (), (), (), False, False, False,
            True, True,
            "canonical left color/degree cell inventories differ, which is impossible under a color-preserving bipartite isomorphism",
        )

    if source_degree.status == "certified_bipartite_degree_alpha_partition":
        if target_degree.status != "certified_bipartite_degree_alpha_partition":
            return PairedUniformNeighborhoodProvenance(
                "undetermined_paired_degree_stage_status",
                n1, n2, float(alpha), source_degree, target_degree, None, None,
                None, None, 0, None, (), (), (), (), True, False, False,
                False, False,
                "degree inventories match but source/target degree stages expose inconsistent progress statuses; fail closed",
            )
        return PairedUniformNeighborhoodProvenance(
            "paired_degree_alpha_partition_preempts_uniform_neighborhood",
            n1, n2, float(alpha), source_degree, target_degree, None, None,
            None, None, 0, None, (), (), (), (), True, False, False,
            False, True,
            "both sides already have the same canonical alpha-bounded degree partition; the uniform-neighborhood relation is not needed",
        )

    required = "certified_bipartite_degree_dominant_cell"
    if source_degree.status != required or target_degree.status != required:
        return PairedUniformNeighborhoodProvenance(
            "undetermined_paired_uniform_neighborhood_degree_gate",
            n1, n2, float(alpha), source_degree, target_degree, None, None,
            None, None, 0, None, (), (), (), (), True, False, False,
            False, False,
            "both sides must expose the exact dominant same-color/same-degree cell before the uniform-neighborhood stage",
        )
    if not source_degree.dominant_twin_free or not target_degree.dominant_twin_free:
        return PairedUniformNeighborhoodProvenance(
            "undetermined_paired_uniform_neighborhood_twins",
            n1, n2, float(alpha), source_degree, target_degree, None, None,
            None, None, 0, None, (), (), (), (), True, False, False,
            False, False,
            "at least one dominant degree cell still contains identical full neighborhoods",
        )
    if (
        source_degree.dominant_signature != target_degree.dominant_signature
        or len(source_degree.dominant_cell) != len(target_degree.dominant_cell)
    ):
        return PairedUniformNeighborhoodProvenance(
            "exact_empty_bipartite_dominant_degree_invariant",
            n1, n2, float(alpha), source_degree, target_degree, None, None,
            None, None, 0, None, (), (), (), (), False, False, False,
            True, True,
            "unique alpha-dominant degree-cell signature or cardinality differs",
        )

    source_h = build_uniform_neighborhood_hypergraph(
        n1, n2, source_edges, source_degree.dominant_cell
    )
    target_h = build_uniform_neighborhood_hypergraph(
        n1, n2, target_edges, target_degree.dominant_cell
    )
    stage_invariant_source = (
        source_h.original_degree,
        source_h.normalized_degree,
        source_h.complemented,
        len(source_h.left_vertices),
        source_h.complete_uniform_hypergraph,
        source_h.test_arity,
    )
    stage_invariant_target = (
        target_h.original_degree,
        target_h.normalized_degree,
        target_h.complemented,
        len(target_h.left_vertices),
        target_h.complete_uniform_hypergraph,
        target_h.test_arity,
    )
    if stage_invariant_source != stage_invariant_target:
        return PairedUniformNeighborhoodProvenance(
            "exact_empty_uniform_neighborhood_stage_invariant",
            n1, n2, float(alpha), source_degree, target_degree, source_h, target_h,
            None, None, len(source_degree.dominant_cell), None,
            (), (), (), (), False, False, False, True, True,
            "normalized neighborhood-hypergraph stage invariants differ across source and target",
        )

    d = int(source_h.normalized_degree)
    complemented = bool(source_h.complemented)
    selected = len(source_h.left_vertices)
    if source_h.complete_uniform_hypergraph:
        if not target_h.complete_uniform_hypergraph:
            raise AssertionError("equal paired stage invariant lost complete-uniform status")
        return PairedUniformNeighborhoodProvenance(
            "certified_paired_uniform_neighborhood_johnson_provenance",
            n1, n2, float(alpha), source_degree, target_degree, source_h, target_h,
            d, complemented, selected, None, (), (), (), (), True, False, True,
            False, True,
            "both dominant twin-free cells are exactly the complete normalized d-uniform neighborhood hypergraph, so their explicit Johnson embeddings are derived equivariantly from the bipartite states",
        )

    if not source_h.test_relation_nonconstant or not target_h.test_relation_nonconstant:
        compatible = source_h.status == target_h.status and source_h.test_colors == target_h.test_colors
        return PairedUniformNeighborhoodProvenance(
            "paired_uniform_neighborhood_constant_relation_residual" if compatible else "undetermined_paired_uniform_neighborhood_relation_stage",
            n1, n2, float(alpha), source_degree, target_degree, source_h, target_h,
            d, complemented, selected, source_h.test_arity,
            tuple(source_h.test_coordinates), tuple(source_h.test_colors),
            tuple(target_h.test_coordinates), tuple(target_h.test_colors),
            Counter(source_h.test_colors) == Counter(target_h.test_colors),
            False, False, False, bool(compatible),
            "the exact rev204 containment-count relation remains constant on at least one side; the separate design-bound theorem child is still required",
        )

    if source_h.test_arity != target_h.test_arity or source_h.test_coordinates != target_h.test_coordinates:
        raise AssertionError("equal paired stage invariants did not yield the same standard t-subset coordinate system")
    multiplicity_ok = Counter(source_h.test_colors) == Counter(target_h.test_colors)
    if not multiplicity_ok:
        return PairedUniformNeighborhoodProvenance(
            "exact_empty_uniform_neighborhood_test_relation_multiplicity",
            n1, n2, float(alpha), source_degree, target_degree, source_h, target_h,
            d, complemented, selected, source_h.test_arity,
            tuple(source_h.test_coordinates), tuple(source_h.test_colors),
            tuple(target_h.test_coordinates), tuple(target_h.test_colors),
            False, True, False, True, True,
            "the equivariantly derived complete V2 test relations have different color multiplicities",
        )

    return PairedUniformNeighborhoodProvenance(
        "certified_paired_uniform_neighborhood_test_relation_provenance",
        n1, n2, float(alpha), source_degree, target_degree, source_h, target_h,
        d, complemented, selected, int(source_h.test_arity),
        tuple(source_h.test_coordinates), tuple(source_h.test_colors),
        tuple(target_h.test_coordinates), tuple(target_h.test_colors),
        True, True, False, False, True,
        "the complete nonconstant V2 containment-count relations were derived by the same exact relabeling-equivariant rev202->rev204 construction and have compatible isomorphism invariants",
    )
