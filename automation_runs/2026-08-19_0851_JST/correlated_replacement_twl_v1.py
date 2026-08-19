from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations, permutations, product
from math import perm
from typing import Hashable, Iterable


@dataclass(frozen=True)
class TWLStableCertificate:
    status: str
    vertex_count: int
    arity: int
    individualized: tuple[int, ...]
    rounds: int
    tuple_states: int
    stable_color_count: int
    point_cells: tuple[tuple[int, ...], ...]
    canonical_signature: tuple
    work_units: int
    exact_stable: bool
    reason: str


@dataclass(frozen=True)
class IndividualizedTWLRecord:
    individualized: tuple[int, ...]
    canonical_signature: tuple
    point_cells: tuple[tuple[int, ...], ...]
    alpha_partition: bool
    rounds: int
    stable_color_count: int
    work_units: int


@dataclass(frozen=True)
class PairedIndividualizationTWLFamily:
    status: str
    vertex_count: int
    arity: int
    family_size: int
    tuple_states_per_run: int
    source_records: tuple[IndividualizedTWLRecord, ...]
    target_records: tuple[IndividualizedTWLRecord, ...]
    source_alpha_witnesses: int
    target_alpha_witnesses: int
    invariant_compatible: bool
    exact_empty: bool
    alpha_partition_certified: bool
    work_units: int
    reason: str


def _freeze(value):
    """Turn common color objects into a deterministic hashable token."""
    if isinstance(value, (str, int, float, bool, bytes, type(None))):
        return (type(value).__name__, value)
    if isinstance(value, tuple):
        return ("tuple", tuple(_freeze(x) for x in value))
    if isinstance(value, list):
        return ("list", tuple(_freeze(x) for x in value))
    if isinstance(value, dict):
        items = ((_freeze(k), _freeze(v)) for k, v in value.items())
        return ("dict", tuple(sorted(items, key=repr)))
    if isinstance(value, (set, frozenset)):
        return ("set", tuple(sorted((_freeze(x) for x in value), key=repr)))
    if isinstance(value, Hashable):
        return (type(value).__qualname__, value)
    return (type(value).__qualname__, repr(value))


def _compress(signatures):
    unique = sorted(set(signatures), key=repr)
    labels = {signature: i for i, signature in enumerate(unique)}
    return [labels[signature] for signature in signatures]


def _equality_pattern(values):
    labels = {}
    out = []
    for value in values:
        if value not in labels:
            labels[value] = len(labels)
        out.append(labels[value])
    return tuple(out)


def _family_size(n: int, k: int) -> int:
    return sum(perm(n, r) for r in range(k))


def stable_correlated_replacement_twl(
    vertex_count: int,
    arity: int,
    colors: Iterable[Hashable],
    *,
    individualized: Iterable[int] = (),
    max_tuple_states: int = 200_000,
    max_work_units: int = 50_000_000,
    max_rounds: int | None = None,
) -> TWLStableCertificate:
    """Compute exact correlated-replacement k-WL on a colored complete k-set relation.

    The update is the standard correlated replacement rule: for an ordered k-tuple
    x and every y in the ground set, collect the k-vector of old colors obtained by
    replacing each coordinate of x by the *same* y.  The multiset of these vectors,
    together with the old color, is the new color.  Initial colors encode equality,
    ordered individualization marks, and the color of the underlying k-subset when
    the tuple has k distinct entries.

    Resource caps are fail-closed.  A certificate with status other than
    ``stable_correlated_replacement_twl`` must not be treated as a WL conclusion.
    """
    n = int(vertex_count)
    k = int(arity)
    palette = tuple(colors)
    individualized = tuple(int(x) for x in individualized)
    if n < 1 or not 1 <= k <= n:
        raise ValueError("invalid vertex_count/arity")
    if len(palette) != len(tuple(combinations(range(n), k))):
        raise ValueError("colors must contain one entry for every k-subset")
    if len(set(individualized)) != len(individualized):
        raise ValueError("individualized sequence must be injective")
    if any(x < 0 or x >= n for x in individualized):
        raise ValueError("individualized vertex outside ground set")
    if max_tuple_states < 1 or max_work_units < 1:
        raise ValueError("resource caps must be positive")

    tuple_states = n ** k
    if tuple_states > max_tuple_states:
        return TWLStableCertificate(
            "twl_tuple_state_cap_closed", n, k, individualized, 0, tuple_states, 0,
            (), (), 0, False,
            "ordered k-tuple state space exceeds the configured exact execution cap",
        )

    coordinates = tuple(combinations(range(n), k))
    relation = {S: _freeze(color) for S, color in zip(coordinates, palette)}
    individualized_labels = {x: i for i, x in enumerate(individualized)}
    strides = tuple(n ** (k - 1 - i) for i in range(k))
    ordered_tuples = tuple(product(range(n), repeat=k))

    initial_signatures = []
    for values in ordered_tuples:
        if len(set(values)) == k:
            relation_color = relation[tuple(sorted(values))]
        else:
            relation_color = ("non_distinct_tuple",)
        initial_signatures.append(
            (
                _equality_pattern(values),
                tuple(individualized_labels.get(x, -1) for x in values),
                relation_color,
            )
        )
    current = _compress(initial_signatures)
    work_units = tuple_states
    rounds = 0
    round_cap = tuple_states if max_rounds is None else int(max_rounds)
    if round_cap < 1:
        raise ValueError("max_rounds must be positive when supplied")

    stable = False
    for _ in range(round_cap):
        round_work = tuple_states * n * k
        if work_units + round_work > max_work_units:
            return TWLStableCertificate(
                "twl_work_cap_closed", n, k, individualized, rounds, tuple_states,
                len(set(current)), (), (), work_units, False,
                "correlated-replacement refinement would exceed the configured exact work cap",
            )

        new_signatures = []
        for index, values in enumerate(ordered_tuples):
            vectors = Counter()
            for y in range(n):
                vector = tuple(
                    current[index + (y - values[i]) * strides[i]] for i in range(k)
                )
                vectors[vector] += 1
            new_signatures.append(
                (current[index], tuple(sorted(vectors.items())))
            )

        refined = _compress(new_signatures)
        work_units += round_work
        rounds += 1
        stable = len(set(refined)) == len(set(current))
        current = refined
        if stable:
            break

    if not stable:
        return TWLStableCertificate(
            "twl_round_cap_closed", n, k, individualized, rounds, tuple_states,
            len(set(current)), (), (), work_units, False,
            "refinement did not stabilize before the configured round cap",
        )

    diagonal_stride = sum(strides)
    point_colors = tuple(current[x * diagonal_stride] for x in range(n))
    buckets = {}
    for x, color in enumerate(point_colors):
        buckets.setdefault(color, []).append(x)
    point_cells = tuple(tuple(buckets[color]) for color in sorted(buckets))
    full_histogram = tuple(sorted(Counter(current).items()))
    point_histogram = tuple(sorted(Counter(point_colors).items()))
    individualized_colors = tuple(point_colors[x] for x in individualized)
    signature = (full_histogram, point_histogram, individualized_colors)

    return TWLStableCertificate(
        "stable_correlated_replacement_twl",
        n,
        k,
        individualized,
        rounds,
        tuple_states,
        len(set(current)),
        point_cells,
        signature,
        work_units,
        True,
        "exact correlated-replacement k-WL reached a stable canonical coloring",
    )


def _individualization_family(
    vertex_count: int,
    arity: int,
    colors,
    *,
    alpha: float,
    max_family_size: int,
    max_tuple_states: int,
    max_work_units: int,
    max_rounds: int | None,
):
    n = int(vertex_count)
    k = int(arity)
    total = _family_size(n, k)
    if total > max_family_size:
        return None, 0, (
            "individualization family size exceeds the configured exact execution cap"
        )

    records = []
    spent = 0
    for length in range(k):
        for sequence in permutations(range(n), length):
            remaining = max_work_units - spent
            if remaining < 1:
                return None, spent, "paired individualization/WL work cap exhausted"
            certificate = stable_correlated_replacement_twl(
                n,
                k,
                colors,
                individualized=sequence,
                max_tuple_states=max_tuple_states,
                max_work_units=remaining,
                max_rounds=max_rounds,
            )
            spent += certificate.work_units
            if not certificate.exact_stable:
                return None, spent, certificate.reason
            largest = max((len(cell) for cell in certificate.point_cells), default=n)
            records.append(
                IndividualizedTWLRecord(
                    sequence,
                    certificate.canonical_signature,
                    certificate.point_cells,
                    largest <= alpha * n + 1e-12,
                    certificate.rounds,
                    certificate.stable_color_count,
                    certificate.work_units,
                )
            )
    return tuple(records), spent, None


def paired_individualization_twl_family(
    vertex_count: int,
    arity: int,
    source_colors,
    target_colors,
    *,
    alpha: float = 0.9,
    max_family_size: int = 200_000,
    max_tuple_states: int = 200_000,
    max_work_units: int = 200_000_000,
    max_rounds: int | None = None,
) -> PairedIndividualizationTWLFamily:
    """Enumerate the full equivariant <=k-1 individualization family and run k-WL.

    Enumerating *all* injective sequences of lengths 0 through k-1 avoids a
    label-dependent choice of a Design-Lemma witness.  The family is carried to
    itself by every relabeling, has size at most 1+n+...+n^(k-1), and therefore is
    quasipolynomial when k=O(log n).  Canonical stable-WL signatures are compared as
    a multiset across the full source/target families.  A mismatch is an exact
    relation-isomorphism obstruction.  Matching families with an alpha-bounded
    diagonal point coloring certify the alpha-partition side of the search; the
    UPCC alternative is deliberately left to a separate verifier.
    """
    n = int(vertex_count)
    k = int(arity)
    if not 0.5 <= alpha < 1.0:
        raise ValueError("alpha must lie in [1/2,1)")
    if max_family_size < 1 or max_work_units < 1:
        raise ValueError("resource caps must be positive")

    family_size = _family_size(n, k)
    tuple_states = n ** k
    source_records, source_work, source_error = _individualization_family(
        n,
        k,
        tuple(source_colors),
        alpha=alpha,
        max_family_size=max_family_size,
        max_tuple_states=max_tuple_states,
        max_work_units=max_work_units,
        max_rounds=max_rounds,
    )
    if source_error is not None:
        return PairedIndividualizationTWLFamily(
            "paired_twl_resource_gate_closed", n, k, family_size, tuple_states,
            (), (), 0, 0, False, False, False, source_work,
            "source exact family execution failed closed: " + source_error,
        )

    target_records, target_work, target_error = _individualization_family(
        n,
        k,
        tuple(target_colors),
        alpha=alpha,
        max_family_size=max_family_size,
        max_tuple_states=max_tuple_states,
        max_work_units=max_work_units,
        max_rounds=max_rounds,
    )
    work = source_work + target_work
    if target_error is not None:
        return PairedIndividualizationTWLFamily(
            "paired_twl_resource_gate_closed", n, k, family_size, tuple_states,
            source_records or (), (), 0, 0, False, False, False, work,
            "target exact family execution failed closed: " + target_error,
        )

    source_inventory = Counter(r.canonical_signature for r in source_records)
    target_inventory = Counter(r.canonical_signature for r in target_records)
    source_alpha = sum(r.alpha_partition for r in source_records)
    target_alpha = sum(r.alpha_partition for r in target_records)
    compatible = source_inventory == target_inventory
    if not compatible:
        return PairedIndividualizationTWLFamily(
            "exact_empty_paired_twl_family_invariant",
            n, k, family_size, tuple_states, source_records, target_records,
            source_alpha, target_alpha, False, True, False, work,
            "full equivariant individualization-family stable-WL signature multisets differ",
        )

    alpha_certified = source_alpha > 0 and target_alpha > 0
    if alpha_certified:
        return PairedIndividualizationTWLFamily(
            "verified_paired_twl_alpha_partition_family",
            n, k, family_size, tuple_states, source_records, target_records,
            source_alpha, target_alpha, True, False, True, work,
            "matching full individualization families contain canonically comparable alpha-bounded stable-WL point partitions",
        )

    return PairedIndividualizationTWLFamily(
        "verified_paired_twl_family_no_alpha_partition",
        n, k, family_size, tuple_states, source_records, target_records,
        source_alpha, target_alpha, True, False, False, work,
        "full paired family is exact and invariant-compatible, but no alpha-bounded point partition was found; the Design-Lemma UPCC alternative remains unverified",
    )
