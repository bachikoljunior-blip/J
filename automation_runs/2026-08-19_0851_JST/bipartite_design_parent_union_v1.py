from __future__ import annotations

from dataclasses import dataclass
from math import log2
from typing import Hashable, Iterable

from ambient_design_tuple_transport_v1 import (
    AmbientDesignTupleCover,
    pair_design_witnesses_inside_ambient_action,
)
from bipartite_parent_action_coset_intersection_v1 import (
    BipartiteParentActionCosetIntersection,
    intersect_parent_bipartite_string_through_right_alignment,
)
from coset_stabilizer_primitives import RightCoset
from paired_bipartite_right_partition_provenance_v1 import _canonical_atom
from permutation_group_schreier import (
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
    validate_perm,
)


@dataclass(frozen=True)
class BipartiteDesignParentUnion:
    status: str
    ambient_cover: AmbientDesignTupleCover
    branch_results: tuple[BipartiteParentActionCosetIntersection, ...]
    structural_branches: int
    branches_checked: int
    nonempty_branches: int
    coset: RightCoset | None
    exact: bool
    complete: bool
    exact_empty: bool
    set_reconstruction_complete: bool
    quasipolynomial_cost_certified: bool
    explicit_union_log2_bookkeeping_bound: float
    reason: str


def _palette(size: int, colors: Iterable[Hashable] | None, default) -> tuple[tuple, ...]:
    raw = tuple(default for _ in range(size)) if colors is None else tuple(colors)
    if len(raw) != size:
        raise ValueError("vertex color sequence length mismatch")
    return tuple(_canonical_atom(x) for x in raw)


def _normalize_edges(left_size: int, right_size: int, edges: Iterable[tuple[int, int]]) -> set[tuple[int, int]]:
    out = set()
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("edge endpoint outside declared bipartite parts")
        out.add((a, b))
    return out


def _maps_state(
    p,
    left_points: tuple[int, ...],
    right_points: tuple[int, ...],
    source_edges: set[tuple[int, int]],
    target_edges: set[tuple[int, int]],
    source_left_colors: tuple[tuple, ...],
    target_left_colors: tuple[tuple, ...],
    source_right_colors: tuple[tuple, ...],
    target_right_colors: tuple[tuple, ...],
) -> bool:
    p = validate_perm(p)
    left_index = {x: i for i, x in enumerate(left_points)}
    right_index = {x: i for i, x in enumerate(right_points)}
    left_image = []
    right_image = []
    for x in left_points:
        y = p[x]
        if y not in left_index:
            return False
        left_image.append(left_index[y])
    for x in right_points:
        y = p[x]
        if y not in right_index:
            return False
        right_image.append(right_index[y])
    for a, aa in enumerate(left_image):
        if source_left_colors[a] != target_left_colors[aa]:
            return False
    for b, bb in enumerate(right_image):
        if source_right_colors[b] != target_right_colors[bb]:
            return False
    mapped = {(left_image[a], right_image[b]) for a, b in source_edges}
    return mapped == target_edges


def solve_design_witness_cover_in_parent_bipartite_action(
    parent_group,
    right_image_generators,
    left_points: Iterable[int],
    right_points: Iterable[int],
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    source_left_colors: Iterable[Hashable] | None = None,
    target_left_colors: Iterable[Hashable] | None = None,
    source_right_colors: Iterable[Hashable] | None = None,
    target_right_colors: Iterable[Hashable] | None = None,
    root_n: int | None = None,
    alpha: float = 0.75,
    max_subsets: int = 200000,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_twl_rounds: int | None = None,
    max_twl_work_units: int = 500000000,
    max_branch_pairs: int = 200000,
    max_partition_states: int = 200000,
    max_auxiliary_degree: int = 200000,
    max_image_group_order: int = 256,
) -> BipartiteDesignParentUnion:
    """Exact set reconstruction for the complete rev204/rev205 Design witness cover.

    The supplied ``right_image_generators`` are generator-paired with the actual
    ``parent_group``. Their generated right action is used by rev205 to derive the
    complete structural witness cover. Every surviving right structural coset is
    then lifted back into the actual parent group and intersected with the complete
    colored bipartite state by rev206's coupled parent-action primitive.

    If all branches are exact, their nonempty intersections are subsets of one
    parent isomorphism set. As in the existing Design tuple full-string union
    routine, one representative plus every child target-automorphism subgroup and
    every inter-branch representative difference generates exactly the target
    automorphism group covered by the union. Completeness of rev205's structural
    cover makes the reconstructed right coset the complete parent isomorphism set.

    This routine certifies set exactness/completeness only. It intentionally does
    not promote the quadratic auxiliary action used by each child to a certified
    global quasipolynomial recurrence edge; recurrence-safe cost transfer is the
    next separate obligation.
    """
    n = int(parent_group.degree)
    left = tuple(int(x) for x in left_points)
    right = tuple(int(x) for x in right_points)
    if len(set(left)) != len(left) or len(set(right)) != len(right):
        raise ValueError("left/right parent points must be distinct within each part")
    if set(left) & set(right):
        raise ValueError("left/right parent parts must be disjoint")
    if any(not 0 <= x < n for x in left + right):
        raise ValueError("left/right parent point outside parent domain")
    if not left or not right:
        raise ValueError("left/right parent parts must be nonempty")
    if root_n is not None and int(root_n) < n:
        raise ValueError("root_n must dominate parent degree")

    images = tuple(validate_perm(q) for q in right_image_generators)
    domain_gens = tuple(parent_group.original_generators)
    if not domain_gens:
        domain_gens = (identity(n),)
    if len(images) != len(domain_gens):
        raise ValueError("one right image generator is required for every parent generator")
    if any(len(q) != len(right) for q in images):
        raise ValueError("right image generator degree mismatch")
    right_group = schreier_stabilizer_chain(images or (identity(len(right)),))

    source_edge_tuple = tuple(source_edges)
    target_edge_tuple = tuple(target_edges)
    cover = pair_design_witnesses_inside_ambient_action(
        right_group,
        len(left),
        len(right),
        source_edge_tuple,
        target_edge_tuple,
        alpha=alpha,
        max_subsets=max_subsets,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_twl_rounds=max_twl_rounds,
        max_twl_work_units=max_twl_work_units,
        max_branch_pairs=max_branch_pairs,
        max_partition_states=max_partition_states,
    )

    if cover.exact_empty:
        return BipartiteDesignParentUnion(
            "exact_empty_design_parent_structural_cover",
            cover, (), cover.original_branch_count, 0, 0, None,
            True, True, True, True, False, 8.0,
            "the complete rev204/rev205 structural cover is already exact empty in the generated parent right action",
        )
    if not cover.exact or not cover.ambient_pairing_complete:
        return BipartiteDesignParentUnion(
            "undetermined_incomplete_design_parent_structural_cover",
            cover, (), cover.original_branch_count, 0, 0, None,
            False, False, False, False, False, 0.0,
            "exact parent full-string reconstruction requires a complete rev205 structural cover",
        )

    candidates = []
    if cover.status == "certified_ambient_design_witness_coset_cover":
        candidates.extend(branch.coset for branch in cover.branches)
    elif cover.status == "certified_unary_ambient_partition_coset":
        transport = cover.unary_transport
        if transport is None or transport.transporter is None or transport.source_stabilizer is None:
            raise AssertionError("certified unary cover must carry an exact partition transporter")
        candidates.append(RightCoset(transport.source_stabilizer, transport.transporter))
    else:
        return BipartiteDesignParentUnion(
            "undetermined_design_parent_cover_not_materialized",
            cover, (), cover.original_branch_count, 0, 0, None,
            False, False, False, False, False, 0.0,
            "rev205 exact status did not materialize the structural candidate cosets required for parent full-string intersection",
        )

    solved = []
    nonempty = []
    for candidate in candidates:
        child = intersect_parent_bipartite_string_through_right_alignment(
            parent_group,
            images,
            candidate,
            left,
            right,
            source_edge_tuple,
            target_edge_tuple,
            source_left_colors=source_left_colors,
            target_left_colors=target_left_colors,
            source_right_colors=source_right_colors,
            target_right_colors=target_right_colors,
            root_n=max(n, int(root_n or n)),
            max_auxiliary_degree=max_auxiliary_degree,
            max_image_group_order=max_image_group_order,
        )
        solved.append(child)
        if not child.exact:
            return BipartiteDesignParentUnion(
                "undetermined_design_parent_full_string_branch",
                cover, tuple(solved), len(candidates), len(solved), len(nonempty), None,
                False, False, False, False, False, 0.0,
                "at least one branch of the complete rev205 structural cover has an unresolved coupled parent full-string intersection",
            )
        if child.coset is not None:
            nonempty.append(child.coset)

    bookkeeping = (
        log2(max(1, len(candidates)))
        + 10.0 * log2(max(2, n))
        + 48.0
    )
    if not nonempty:
        return BipartiteDesignParentUnion(
            "exact_empty_design_parent_full_string_union",
            cover, tuple(solved), len(candidates), len(solved), 0, None,
            True, True, True, True, False, bookkeeping,
            "every branch in the complete rev205 structural cover has an exact empty coupled parent full-string intersection",
        )

    source_edges_set = _normalize_edges(len(left), len(right), source_edge_tuple)
    target_edges_set = _normalize_edges(len(left), len(right), target_edge_tuple)
    source_lc = _palette(len(left), source_left_colors, 0)
    target_lc = _palette(len(left), target_left_colors, 0)
    source_rc = _palette(len(right), source_right_colors, 1)
    target_rc = _palette(len(right), target_right_colors, 1)

    r0 = nonempty[0].representative
    if not parent_group.contains(r0) or not _maps_state(
        r0, left, right, source_edges_set, target_edges_set,
        source_lc, target_lc, source_rc, target_rc,
    ):
        raise AssertionError("exact child representative is not a parent bipartite isomorphism")

    generators = []
    for child_coset in nonempty:
        ri = child_coset.representative
        if not parent_group.contains(ri) or not _maps_state(
            ri, left, right, source_edges_set, target_edges_set,
            source_lc, target_lc, source_rc, target_rc,
        ):
            raise AssertionError("exact child representative is not a parent bipartite isomorphism")
        for g in child_coset.subgroup.original_generators:
            if not parent_group.contains(g) or not _maps_state(
                g, left, right, target_edges_set, target_edges_set,
                target_lc, target_lc, target_rc, target_rc,
            ):
                raise AssertionError("exact child subgroup contains a non-target automorphism")
            generators.append(g)
        delta = compose(inverse(r0), ri)
        if not parent_group.contains(delta) or not _maps_state(
            delta, left, right, target_edges_set, target_edges_set,
            target_lc, target_lc, target_rc, target_rc,
        ):
            raise AssertionError("inter-branch representative difference is not a target automorphism")
        generators.append(delta)

    target_aut = schreier_stabilizer_chain(generators or (identity(n),))
    return BipartiteDesignParentUnion(
        "exact_design_parent_full_string_union_coset",
        cover, tuple(solved), len(candidates), len(solved), len(nonempty),
        RightCoset(target_aut, r0), True, True, False, True, False, bookkeeping,
        "every candidate in the complete rev205 structural cover was exactly intersected inside the actual coupled parent action and the complete nonempty union was reconstructed as one target-automorphism parent right coset",
    )
