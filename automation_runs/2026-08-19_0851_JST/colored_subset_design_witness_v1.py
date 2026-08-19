from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations, permutations
from math import comb, log2
from typing import Hashable, Iterable

from colored_subset_symmetry_defect_v1 import exact_colored_subset_symmetry_defect


@dataclass(frozen=True)
class IndividualizedWLOutcome:
    individualized: tuple[int, ...]
    status: str
    point_cells: tuple[tuple[int, ...], ...]
    largest_point_cell: int
    dominant_cell: tuple[int, ...]
    dominant_pair_color_count: int
    refinement_rounds: int
    reason: str


@dataclass(frozen=True)
class DesignWitnessFamily:
    status: str
    vertex_count: int
    arity: int
    alpha: float
    theorem_parameter_gate: bool
    symmetry_defect_gate: bool
    largest_symmetric_class: int
    minimal_individualization_length: int | None
    witness_tuples: tuple[tuple[int, ...], ...]
    witness_kinds: tuple[str, ...]
    states_checked: int
    auxiliary_vertices: int
    max_refinement_rounds_used: int
    local_log2_cost_bound: float
    exact: bool
    reason: str


def _falling_factorial(n: int, r: int) -> int:
    out = 1
    for i in range(r):
        out *= n - i
    return out


def _normalize_matrix(signatures):
    universe = sorted({x for row in signatures for x in row}, key=repr)
    labels = {x: i for i, x in enumerate(universe)}
    return tuple(tuple(labels[x] for x in row) for row in signatures)


def _matrix_color_class_count(matrix) -> int:
    return len({c for row in matrix for c in row})


def _incidence_two_wl(
    vertex_count: int,
    arity: int,
    colors: tuple[Hashable, ...],
    individualized: tuple[int, ...],
    *,
    alpha: float,
    max_rounds: int,
) -> IndividualizedWLOutcome:
    """Run exact 2-WL on the colored point--t-subset incidence structure.

    Relation coordinates are explicit vertices colored by the original t-subset
    color. Point vertices are a separate type. The supplied ordered tuple is
    individualized by distinct point colors. This construction is canonical
    relative to that tuple and retains the complete higher-arity relation rather
    than only its codegrees.

    Stabilization is tested on the induced partition, not on the incidental
    integer IDs assigned to color classes. Each refinement signature contains
    the previous color, so classes can split but never merge. Consequently the
    partition is stable exactly when the number of color classes stops growing;
    numeric color IDs may still be canonically renumbered between rounds.
    """
    v = int(vertex_count)
    t = int(arity)
    coords = tuple(combinations(range(v), t))
    if len(colors) != len(coords):
        raise ValueError("colors must contain one value for every t-subset")
    if len(set(individualized)) != len(individualized):
        raise ValueError("individualized tuple must contain distinct vertices")
    if any(u < 0 or u >= v for u in individualized):
        raise ValueError("individualized vertex outside domain")

    relation_sets = tuple(frozenset(S) for S in coords)
    m = v + len(coords)
    tuple_rank = {u: i for i, u in enumerate(individualized)}
    vertex_colors = [
        ("point", "individualized", tuple_rank[u]) if u in tuple_rank else ("point", "ordinary")
        for u in range(v)
    ] + [("relation", colors[j]) for j in range(len(coords))]

    initial = []
    for i in range(m):
        row = []
        for j in range(m):
            if i == j:
                row.append(("diag", vertex_colors[i]))
                continue
            incidence = False
            if i < v <= j:
                incidence = i in relation_sets[j - v]
            elif j < v <= i:
                incidence = j in relation_sets[i - v]
            row.append(("pair", vertex_colors[i], vertex_colors[j], incidence))
        initial.append(tuple(row))
    current = _normalize_matrix(tuple(initial))

    rounds = 0
    current_class_count = _matrix_color_class_count(current)
    while True:
        signatures = []
        for i in range(m):
            row = []
            for j in range(m):
                counts = Counter((current[i][w], current[w][j]) for w in range(m))
                row.append((current[i][j], tuple(sorted(counts.items()))))
            signatures.append(tuple(row))
        refined = _normalize_matrix(tuple(signatures))
        rounds += 1
        refined_class_count = _matrix_color_class_count(refined)
        if refined_class_count < current_class_count:
            raise AssertionError("2-WL refinement merged an existing color class")
        if refined_class_count == current_class_count:
            current = refined
            break
        if rounds >= max_rounds:
            return IndividualizedWLOutcome(
                individualized,
                "undetermined_wl_round_limit",
                (),
                v,
                (),
                0,
                rounds,
                "2-WL on the explicit incidence structure did not stabilize within max_rounds",
            )
        current = refined
        current_class_count = refined_class_count

    buckets = defaultdict(list)
    for u in range(v):
        buckets[current[u][u]].append(u)
    cells = tuple(sorted((tuple(xs) for xs in buckets.values()), key=lambda C: (len(C), C)))
    largest = max((len(C) for C in cells), default=0)
    dominant = max(cells, key=lambda C: (len(C), tuple(-x for x in C))) if cells else ()
    no_alpha_dominant = largest <= alpha * v + 1e-12
    pair_colors = {
        current[u][w]
        for u in dominant
        for w in dominant
        if u != w
    }
    nonclique = bool(dominant) and len(pair_colors) > 1

    if no_alpha_dominant:
        status = "certified_alpha_coloring"
        reason = "stable incidence 2-WL gives a canonical point coloring with every color class at most alpha*v"
    elif nonclique:
        status = "certified_dominant_nonclique_coherent_fiber"
        reason = "stable incidence 2-WL leaves an alpha-dominant point fiber whose induced ordered-pair colors are nontrivial"
    else:
        status = "stable_wl_without_design_witness"
        reason = "stable incidence 2-WL has an alpha-dominant point fiber and its induced off-diagonal pair color is a clique"

    return IndividualizedWLOutcome(
        individualized,
        status,
        cells,
        largest,
        tuple(dominant),
        len(pair_colors),
        rounds,
        reason,
    )


def find_colored_subset_design_witness_family(
    vertex_count: int,
    arity: int,
    colors: Iterable[Hashable],
    *,
    alpha: float = 0.9,
    max_states: int = 200000,
    max_wl_vertices: int = 512,
    max_wl_rounds: int = 4096,
) -> DesignWitnessFamily:
    """Enumerate the complete minimal Design-Lemma witness branch family.

    Preconditions are checked mechanically: 2 <= arity <= v/2 and the exact
    symmetry-defect gate. For each ell < arity, *all* ordered ell-tuples are
    processed before accepting that level. Therefore the returned set of witness
    tuples is label-invariant as a family even though no arbitrary representative
    tuple is selected. Each tuple is individualized and the full colored
    t-subset relation is converted to an incidence structure whose exact stable
    2-WL closure supplies either an alpha-coloring or a non-clique coherent point
    fiber. If any completeness/resource gate prevents exhaustive verification,
    the routine fails closed.
    """
    v = int(vertex_count)
    t = int(arity)
    palette = tuple(colors)
    if v < 1 or not 1 <= t <= v:
        raise ValueError("invalid vertex_count/arity")
    if not 0.5 <= alpha < 1.0:
        raise ValueError("alpha must lie in [1/2,1)")
    if max_states < 1 or max_wl_vertices < 1 or max_wl_rounds < 1:
        raise ValueError("resource limits must be positive")
    expected = comb(v, t)
    if len(palette) != expected:
        raise ValueError("colors must contain one value for every t-subset")

    theorem_gate = 2 <= t <= v // 2
    symmetry = exact_colored_subset_symmetry_defect(v, t, palette, alpha=alpha)
    auxiliary_vertices = v + expected
    if not theorem_gate:
        return DesignWitnessFamily(
            "undetermined_design_theorem_parameter_gate",
            v, t, float(alpha), False, symmetry.design_gate_certified,
            symmetry.largest_symmetric_class, None, (), (), 0,
            auxiliary_vertices, 0, 0.0, False,
            "Design-Lemma parameter gate requires 2 <= arity <= floor(v/2)",
        )
    if not symmetry.design_gate_certified:
        return DesignWitnessFamily(
            "undetermined_design_symmetry_defect_gate",
            v, t, float(alpha), True, False,
            symmetry.largest_symmetric_class, None, (), (), 0,
            auxiliary_vertices, 0, 0.0, False,
            "exact largest symmetric subset exceeds alpha*v, so the Design-Lemma symmetry-defect hypothesis is not certified",
        )
    if auxiliary_vertices > max_wl_vertices:
        bound = log2(max(2, auxiliary_vertices)) * 4.0 + t * log2(max(2, v)) + 32.0
        return DesignWitnessFamily(
            "undetermined_design_explicit_wl_vertex_limit",
            v, t, float(alpha), True, True,
            symmetry.largest_symmetric_class, None, (), (), 0,
            auxiliary_vertices, 0, bound, False,
            "the theorem gate is certified, but the explicit incidence 2-WL realization exceeds max_wl_vertices",
        )

    states_checked = 0
    max_rounds_used = 0
    for ell in range(t):
        level_count = _falling_factorial(v, ell)
        if states_checked + level_count > max_states:
            bound = log2(max(2, states_checked + level_count)) + 4.0 * log2(max(2, auxiliary_vertices)) + 32.0
            return DesignWitnessFamily(
                "undetermined_design_individualization_state_limit",
                v, t, float(alpha), True, True,
                symmetry.largest_symmetric_class, None, (), (), states_checked,
                auxiliary_vertices, max_rounds_used, bound, False,
                "complete enumeration of the next individualization level would exceed max_states",
            )

        witnesses = []
        kinds = []
        for individualized in permutations(range(v), ell):
            outcome = _incidence_two_wl(
                v, t, palette, tuple(individualized),
                alpha=alpha,
                max_rounds=max_wl_rounds,
            )
            states_checked += 1
            max_rounds_used = max(max_rounds_used, outcome.refinement_rounds)
            if outcome.status == "undetermined_wl_round_limit":
                return DesignWitnessFamily(
                    outcome.status,
                    v, t, float(alpha), True, True,
                    symmetry.largest_symmetric_class, None, (), (), states_checked,
                    auxiliary_vertices, max_rounds_used, 0.0, False,
                    outcome.reason,
                )
            if outcome.status in {
                "certified_alpha_coloring",
                "certified_dominant_nonclique_coherent_fiber",
            }:
                witnesses.append(tuple(individualized))
                kinds.append(outcome.status)

        if witnesses:
            # We completed the whole first successful level, so the branch family
            # and the minimal length are invariant under every relation isomorphism.
            local_bound = (
                log2(max(2, states_checked))
                + 4.0 * log2(max(2, auxiliary_vertices))
                + 2.0 * log2(max(2, max_rounds_used))
                + 48.0
            )
            return DesignWitnessFamily(
                "certified_design_witness_family",
                v, t, float(alpha), True, True,
                symmetry.largest_symmetric_class, ell,
                tuple(witnesses), tuple(kinds), states_checked,
                auxiliary_vertices, max_rounds_used, local_bound, True,
                "all ordered tuples through the first successful individualization level were exhaustively checked; the complete minimal witness family is canonical as a set of branches",
            )

    local_bound = (
        log2(max(2, states_checked))
        + 4.0 * log2(max(2, auxiliary_vertices))
        + 2.0 * log2(max(2, max_rounds_used))
        + 48.0
    )
    return DesignWitnessFamily(
        "design_witness_absent_despite_certified_preconditions",
        v, t, float(alpha), True, True,
        symmetry.largest_symmetric_class, None, (), (), states_checked,
        auxiliary_vertices, max_rounds_used, local_bound, True,
        "all ell<arity individualizations stabilized without either certified Design-Lemma outcome; this is a falsification signal for the chosen incidence-WL realization and must not be treated as progress",
    )
