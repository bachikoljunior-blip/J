from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations, permutations, product
from math import comb, log2
from typing import Iterable

from colored_subset_symmetry_defect_v1 import exact_colored_subset_symmetry_defect


@dataclass(frozen=True)
class StableSubsetTWL:
    status: str
    vertex_count: int
    arity: int
    individualized: tuple[int, ...]
    rounds: int
    tuple_states: int
    stable_color_count: int
    point_colors: tuple[int, ...]
    pair_colors: tuple[tuple[int, ...], ...]
    canonical_signature: tuple
    work_units: int
    exact_stable: bool
    reason: str


@dataclass(frozen=True)
class ExactTWLDesignOutcome:
    individualized: tuple[int, ...]
    status: str
    point_cells: tuple[tuple[int, ...], ...]
    output_partition: tuple[tuple[int, ...], ...]
    dominant_cell: tuple[int, ...]
    two_skeleton_rank: int
    constituent_components: tuple[tuple[int, ...], ...]
    stable_signature: tuple
    rounds: int
    work_units: int
    exact: bool
    reason: str


@dataclass(frozen=True)
class ExactTWLDesignFamily:
    status: str
    vertex_count: int
    arity: int
    alpha: float
    theorem_parameter_gate: bool
    symmetry_defect_gate: bool
    minimal_individualization_length: int | None
    witness_outcomes: tuple[ExactTWLDesignOutcome, ...]
    states_checked: int
    tuple_states_per_run: int
    work_units: int
    local_log2_cost_bound: float
    exact: bool
    reason: str


@dataclass(frozen=True)
class PairedExactTWLDesignFamily:
    status: str
    source: ExactTWLDesignFamily
    target: ExactTWLDesignFamily
    invariant_compatible: bool
    exact_empty: bool
    complete: bool
    reason: str


def _freeze(value):
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return (type(value).__name__, value)
    if isinstance(value, tuple):
        return ("tuple", tuple(_freeze(x) for x in value))
    if isinstance(value, list):
        return ("list", tuple(_freeze(x) for x in value))
    if isinstance(value, dict):
        items = tuple(sorted(((_freeze(k), _freeze(v)) for k, v in value.items()), key=repr))
        return ("dict", items)
    if isinstance(value, (set, frozenset)):
        return ("set", tuple(sorted((_freeze(x) for x in value), key=repr)))
    raise TypeError("relation colors must be recursively composed of primitive/list/tuple/dict/set values")


def _compress(signatures):
    universe = sorted(set(signatures), key=repr)
    labels = {signature: i for i, signature in enumerate(universe)}
    return [labels[signature] for signature in signatures]


def _equality_pattern(values):
    ids = {}
    out = []
    for value in values:
        if value not in ids:
            ids[value] = len(ids)
        out.append(ids[value])
    return tuple(out)


def stable_colored_subset_twl(
    vertex_count: int,
    arity: int,
    colors: Iterable,
    *,
    individualized: Iterable[int] = (),
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_work_units: int = 100000000,
) -> StableSubsetTWL:
    """Exact correlated-replacement k-WL on a complete colored k-subset relation.

    Ordered k-tuples are initially colored by equality type, ordered constants,
    and the underlying k-subset color when all coordinates are distinct. Every
    refinement round uses the correlated replacement profile: for each y, the
    k-vector of old colors obtained by replacing each coordinate by the same y.
    This is the standard k-WL update needed by the Design-Lemma proof boundary.
    """
    n = int(vertex_count)
    k = int(arity)
    palette = tuple(colors)
    individualized = tuple(int(x) for x in individualized)
    if n < 1 or not 1 <= k <= n:
        raise ValueError("invalid vertex_count/arity")
    if len(palette) != comb(n, k):
        raise ValueError("colors must contain one entry for every k-subset")
    if len(set(individualized)) != len(individualized):
        raise ValueError("individualized sequence must be injective")
    if any(x < 0 or x >= n for x in individualized):
        raise ValueError("individualized vertex outside the ground set")
    if max_tuple_states < 1 or max_work_units < 1:
        raise ValueError("resource caps must be positive")

    tuple_states = n ** k
    if tuple_states > max_tuple_states:
        return StableSubsetTWL(
            "twl_tuple_state_cap_closed", n, k, individualized, 0, tuple_states,
            0, (), (), (), 0, False,
            "ordered k-tuple state space exceeds the configured exact execution cap",
        )

    coords = tuple(combinations(range(n), k))
    relation = {S: _freeze(color) for S, color in zip(coords, palette)}
    marks = {x: i for i, x in enumerate(individualized)}
    ordered = tuple(product(range(n), repeat=k))
    strides = tuple(n ** (k - 1 - i) for i in range(k))

    signatures = []
    for values in ordered:
        relation_color = (
            relation[tuple(sorted(values))]
            if len(set(values)) == k
            else ("non_distinct_tuple",)
        )
        signatures.append(
            (
                _equality_pattern(values),
                tuple(marks.get(x, -1) for x in values),
                relation_color,
            )
        )
    current = _compress(signatures)
    work_units = tuple_states
    rounds = 0
    round_cap = tuple_states if max_rounds is None else int(max_rounds)
    if round_cap < 1:
        raise ValueError("max_rounds must be positive when supplied")

    stable = False
    for _ in range(round_cap):
        round_work = tuple_states * n * k
        if work_units + round_work > max_work_units:
            return StableSubsetTWL(
                "twl_work_cap_closed", n, k, individualized, rounds, tuple_states,
                len(set(current)), (), (), (), work_units, False,
                "the next exact correlated-replacement round would exceed max_work_units",
            )
        refined_signatures = []
        for index, values in enumerate(ordered):
            replacement_vectors = Counter()
            for y in range(n):
                vector = tuple(
                    current[index + (y - values[i]) * strides[i]] for i in range(k)
                )
                replacement_vectors[vector] += 1
            refined_signatures.append(
                (current[index], tuple(sorted(replacement_vectors.items())))
            )
        refined = _compress(refined_signatures)
        rounds += 1
        work_units += round_work
        old_count = len(set(current))
        new_count = len(set(refined))
        if new_count < old_count:
            raise AssertionError("k-WL refinement merged an existing color class")
        current = refined
        if new_count == old_count:
            stable = True
            break

    if not stable:
        return StableSubsetTWL(
            "twl_round_cap_closed", n, k, individualized, rounds, tuple_states,
            len(set(current)), (), (), (), work_units, False,
            "k-WL did not stabilize before the configured round cap",
        )

    def tuple_index(values):
        return sum(int(values[i]) * strides[i] for i in range(k))

    point_colors = tuple(current[tuple_index((x,) * k)] for x in range(n))
    pair_colors = tuple(
        tuple(current[tuple_index((x,) + (y,) * (k - 1))] for y in range(n))
        for x in range(n)
    )
    signature = (
        tuple(sorted(Counter(current).items())),
        tuple(sorted(Counter(point_colors).items())),
        tuple(sorted(Counter(c for row in pair_colors for c in row).items())),
        tuple(point_colors[x] for x in individualized),
    )
    return StableSubsetTWL(
        "stable_colored_subset_twl", n, k, individualized, rounds, tuple_states,
        len(set(current)), point_colors, pair_colors, signature, work_units, True,
        "exact correlated-replacement k-WL reached a stable canonical coloring",
    )


def _cells_from_colors(colors):
    buckets = defaultdict(list)
    for x, color in enumerate(colors):
        buckets[color].append(x)
    return tuple(sorted((tuple(xs) for xs in buckets.values()), key=lambda C: (len(C), C)))


def _weak_components(vertices, pair_colors, color):
    vertices = tuple(vertices)
    parent = {x: x for x in vertices}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for x in vertices:
        for y in vertices:
            if x != y and pair_colors[x][y] == color:
                union(x, y)
    buckets = defaultdict(list)
    for x in vertices:
        buckets[find(x)].append(x)
    return tuple(sorted((tuple(xs) for xs in buckets.values()), key=lambda C: (len(C), C)))


def _verify_induced_coherence(vertices, pair_colors):
    vertices = tuple(vertices)
    relation_colors = sorted(
        {pair_colors[x][y] for x in vertices for y in vertices}
    )
    transpose = {}
    for color in relation_colors:
        reverse = {
            pair_colors[y][x]
            for x in vertices
            for y in vertices
            if pair_colors[x][y] == color
        }
        if len(reverse) != 1:
            return False, "pair-color transpose is not well-defined"
        transpose[color] = next(iter(reverse))

    reference = {}
    for x in vertices:
        for y in vertices:
            color = pair_colors[x][y]
            counts = tuple(sorted(Counter(
                (pair_colors[x][z], pair_colors[z][y]) for z in vertices
            ).items()))
            if color in reference and reference[color] != counts:
                return False, "2-skeleton structure constants depend on the representative pair"
            reference[color] = counts
    return True, "induced stable 2-skeleton satisfies exact coherent-configuration structure constants"


def classify_stable_twl_design(
    certificate: StableSubsetTWL,
    *,
    alpha: float = 0.9,
) -> ExactTWLDesignOutcome:
    if not 0.5 <= alpha < 1.0:
        raise ValueError("alpha must lie in [1/2,1)")
    if not certificate.exact_stable:
        return ExactTWLDesignOutcome(
            certificate.individualized, certificate.status, (), (), (), 0, (), (),
            certificate.rounds, certificate.work_units, False, certificate.reason,
        )

    n = certificate.vertex_count
    cells = _cells_from_colors(certificate.point_colors)
    largest = max((len(C) for C in cells), default=0)
    if largest <= alpha * n + 1e-12:
        return ExactTWLDesignOutcome(
            certificate.individualized,
            "certified_twl_alpha_coloring",
            cells,
            cells,
            (),
            0,
            (),
            certificate.canonical_signature,
            certificate.rounds,
            certificate.work_units,
            True,
            "stable k-WL point colors form a canonical alpha-bounded coloring",
        )

    dominant = max(cells, key=lambda C: (len(C), tuple(-x for x in C)))
    if sum(1 for C in cells if len(C) > alpha * n + 1e-12) != 1:
        return ExactTWLDesignOutcome(
            certificate.individualized,
            "twl_dominant_fiber_uniqueness_failure",
            cells, (), dominant, 0, (), certificate.canonical_signature,
            certificate.rounds, certificate.work_units, False,
            "alpha>=1/2 should allow at most one alpha-dominant point color class",
        )

    pair = certificate.pair_colors
    coherent, coherence_reason = _verify_induced_coherence(dominant, pair)
    if not coherent:
        return ExactTWLDesignOutcome(
            certificate.individualized,
            "twl_two_skeleton_coherence_failure",
            cells, (), dominant, 0, (), certificate.canonical_signature,
            certificate.rounds, certificate.work_units, False,
            coherence_reason,
        )

    diagonal_colors = {pair[x][x] for x in dominant}
    if len(diagonal_colors) != 1:
        return ExactTWLDesignOutcome(
            certificate.individualized,
            "twl_dominant_fiber_not_homogeneous",
            cells, (), dominant, 0, (), certificate.canonical_signature,
            certificate.rounds, certificate.work_units, False,
            "dominant point-color fiber has more than one diagonal 2-skeleton color",
        )
    diagonal = next(iter(diagonal_colors))
    if any(pair[x][y] == diagonal for x in dominant for y in dominant if x != y):
        return ExactTWLDesignOutcome(
            certificate.individualized,
            "twl_diagonal_color_leaks_off_diagonal",
            cells, (), dominant, 0, (), certificate.canonical_signature,
            certificate.rounds, certificate.work_units, False,
            "induced 2-skeleton diagonal color also occurs off the diagonal",
        )

    relation_colors = {pair[x][y] for x in dominant for y in dominant}
    off_diagonal = sorted(relation_colors - {diagonal})
    rank = len(relation_colors)
    for color in off_diagonal:
        components = _weak_components(dominant, pair, color)
        if len(components) <= 1:
            continue
        sizes = {len(C) for C in components}
        if len(sizes) != 1:
            return ExactTWLDesignOutcome(
                certificate.individualized,
                "twl_imprimitive_component_equipartition_failure",
                cells, (), dominant, rank, components, certificate.canonical_signature,
                certificate.rounds, certificate.work_units, False,
                "a disconnected homogeneous constituent did not produce equal-size components",
            )
        output = tuple(sorted(
            tuple(C for C in cells if C != dominant) + components,
            key=lambda C: (len(C), C),
        ))
        if max(map(len, output), default=0) > alpha * n + 1e-12:
            return ExactTWLDesignOutcome(
                certificate.individualized,
                "twl_imprimitive_partition_not_alpha_bounded",
                cells, output, dominant, rank, components, certificate.canonical_signature,
                certificate.rounds, certificate.work_units, False,
                "disconnected constituent components failed the required alpha bound",
            )
        return ExactTWLDesignOutcome(
            certificate.individualized,
            "certified_twl_imprimitive_alpha_partition",
            cells, output, dominant, rank, components, certificate.canonical_signature,
            certificate.rounds, certificate.work_units, True,
            coherence_reason + "; a disconnected constituent yields a canonical alpha-bounded equipartition",
        )

    if rank >= 3:
        return ExactTWLDesignOutcome(
            certificate.individualized,
            "certified_twl_upcc",
            cells, (), dominant, rank, (), certificate.canonical_signature,
            certificate.rounds, certificate.work_units, True,
            coherence_reason + "; every non-diagonal constituent is weakly connected and rank>=3, certifying a uniprimitive coherent configuration on the dominant fiber",
        )
    if rank == 2:
        return ExactTWLDesignOutcome(
            certificate.individualized,
            "stable_twl_clique_continue",
            cells, (), dominant, rank, (), certificate.canonical_signature,
            certificate.rounds, certificate.work_units, True,
            coherence_reason + "; the dominant homogeneous 2-skeleton has rank 2 and is the clique continuation case",
        )
    return ExactTWLDesignOutcome(
        certificate.individualized,
        "twl_invalid_homogeneous_rank",
        cells, (), dominant, rank, (), certificate.canonical_signature,
        certificate.rounds, certificate.work_units, False,
        "dominant homogeneous 2-skeleton has invalid rank below 2",
    )


def find_exact_twl_design_witness_family(
    vertex_count: int,
    arity: int,
    colors: Iterable,
    *,
    alpha: float = 0.9,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_work_units: int = 500000000,
) -> ExactTWLDesignFamily:
    """Execute the complete <=k-1 individualization loop with exact standard k-WL.

    The first successful level is exhausted in full. Therefore its witness family
    is equivariant under every relabeling and no arbitrary representative is
    selected. Accepted outcomes are exactly the alpha-coloring, imprimitive split,
    and UPCC branches of the Design-Lemma Split-or-UPCC procedure.
    """
    n = int(vertex_count)
    k = int(arity)
    palette = tuple(colors)
    if n < 1 or not 1 <= k <= n:
        raise ValueError("invalid vertex_count/arity")
    if not 0.75 <= alpha < 1.0:
        raise ValueError("Extended Design Lemma alpha must lie in [3/4,1)")
    if len(palette) != comb(n, k):
        raise ValueError("colors must contain one entry for every k-subset")
    if max_states < 1 or max_work_units < 1:
        raise ValueError("resource caps must be positive")

    theorem_gate = 2 <= k <= n // 4
    symmetry = exact_colored_subset_symmetry_defect(n, k, palette, alpha=alpha)
    tuple_states = n ** k
    if not theorem_gate:
        return ExactTWLDesignFamily(
            "undetermined_twl_design_theorem_parameter_gate", n, k, float(alpha),
            False, symmetry.design_gate_certified, None, (), 0, tuple_states, 0, 0.0,
            False, "Extended Design Lemma parameter gate requires 2<=arity<=floor(n/4)",
        )
    if not symmetry.design_gate_certified:
        return ExactTWLDesignFamily(
            "undetermined_twl_design_symmetry_defect_gate", n, k, float(alpha),
            True, False, None, (), 0, tuple_states, 0, 0.0, False,
            "exact symmetry-defect hypothesis is not certified",
        )
    if tuple_states > max_tuple_states:
        return ExactTWLDesignFamily(
            "undetermined_twl_design_tuple_state_cap", n, k, float(alpha),
            True, True, None, (), 0, tuple_states, 0,
            log2(max(2, tuple_states)) + 32.0, False,
            "standard k-WL tuple state space exceeds the configured exact cap",
        )

    states_checked = 0
    work = 0
    accepted = {
        "certified_twl_alpha_coloring",
        "certified_twl_imprimitive_alpha_partition",
        "certified_twl_upcc",
    }
    for ell in range(k):
        level_count = 1
        for i in range(ell):
            level_count *= n - i
        if states_checked + level_count > max_states:
            return ExactTWLDesignFamily(
                "undetermined_twl_design_family_state_cap", n, k, float(alpha),
                True, True, None, (), states_checked, tuple_states, work,
                log2(max(2, states_checked + level_count)) + log2(max(2, work)) + 32.0,
                False,
                "complete enumeration of the next individualization level would exceed max_states",
            )

        witnesses = []
        for individualized in permutations(range(n), ell):
            remaining = max_work_units - work
            if remaining < 1:
                return ExactTWLDesignFamily(
                    "undetermined_twl_design_work_cap", n, k, float(alpha),
                    True, True, None, (), states_checked, tuple_states, work,
                    log2(max(2, work)) + 32.0, False,
                    "global exact k-WL work budget was exhausted",
                )
            stable = stable_colored_subset_twl(
                n, k, palette,
                individualized=individualized,
                max_tuple_states=max_tuple_states,
                max_rounds=max_rounds,
                max_work_units=remaining,
            )
            states_checked += 1
            work += stable.work_units
            outcome = classify_stable_twl_design(stable, alpha=alpha)
            if not outcome.exact:
                return ExactTWLDesignFamily(
                    outcome.status, n, k, float(alpha), True, True, None, (),
                    states_checked, tuple_states, work,
                    log2(max(2, work)) + 32.0, False, outcome.reason,
                )
            if outcome.status in accepted:
                witnesses.append(outcome)

        if witnesses:
            bound = (
                log2(max(2, states_checked))
                + log2(max(2, work))
                + 2.0 * k * log2(max(2, n))
                + 48.0
            )
            return ExactTWLDesignFamily(
                "certified_exact_twl_design_witness_family", n, k, float(alpha),
                True, True, ell, tuple(witnesses), states_checked, tuple_states,
                work, bound, True,
                "the complete first successful <=k-1 individualization level was exhausted using exact standard k-WL and mechanical Split-or-UPCC classification",
            )

    bound = log2(max(2, states_checked)) + log2(max(2, work)) + 48.0
    return ExactTWLDesignFamily(
        "exact_twl_design_falsification_signal", n, k, float(alpha), True, True,
        None, (), states_checked, tuple_states, work, bound, True,
        "all <=k-1 individualizations reached stable exact k-WL without a Split-or-UPCC success despite certified Design-Lemma preconditions; treat this as an implementation/theorem-encoding falsification signal, not progress",
    )


def _witness_inventory(family: ExactTWLDesignFamily):
    return Counter(
        (
            outcome.status,
            outcome.stable_signature,
            tuple(sorted(map(len, outcome.point_cells))),
            tuple(sorted(map(len, outcome.output_partition))),
            len(outcome.dominant_cell),
            outcome.two_skeleton_rank,
            tuple(sorted(map(len, outcome.constituent_components))),
        )
        for outcome in family.witness_outcomes
    )


def paired_exact_twl_design_witness_families(
    vertex_count: int,
    arity: int,
    source_colors,
    target_colors,
    **kwargs,
) -> PairedExactTWLDesignFamily:
    source = find_exact_twl_design_witness_family(
        vertex_count, arity, source_colors, **kwargs
    )
    target = find_exact_twl_design_witness_family(
        vertex_count, arity, target_colors, **kwargs
    )
    if not source.exact or not target.exact:
        return PairedExactTWLDesignFamily(
            "undetermined_paired_exact_twl_design_family", source, target,
            False, False, False,
            "at least one exact standard-k-WL Design family failed a theorem/resource/mechanical gate",
        )
    if source.status == "exact_twl_design_falsification_signal" or target.status == "exact_twl_design_falsification_signal":
        return PairedExactTWLDesignFamily(
            "paired_exact_twl_design_falsification_signal", source, target,
            False, False, False,
            "a certified-precondition side exhausted <=k-1 individualization without a Design-Lemma outcome",
        )
    compatible = (
        source.minimal_individualization_length == target.minimal_individualization_length
        and _witness_inventory(source) == _witness_inventory(target)
    )
    if not compatible:
        return PairedExactTWLDesignFamily(
            "exact_empty_paired_twl_design_invariant", source, target,
            False, True, True,
            "first-successful-level exact k-WL Design witness invariants differ, which is impossible under a color-preserving relation isomorphism",
        )
    return PairedExactTWLDesignFamily(
        "certified_paired_exact_twl_design_family", source, target,
        True, False, True,
        "source and target have identical complete first-successful-level exact k-WL Design witness invariants",
    )
