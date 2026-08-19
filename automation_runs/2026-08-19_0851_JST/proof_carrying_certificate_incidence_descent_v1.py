from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log2
from typing import Hashable, Iterable

from babai_local_certificate_parameter_gate_v1 import babai_local_certificate_parameter_gate
from permutation_group_schreier import StabilizerChain, identity


@dataclass(frozen=True)
class CertificateIncidenceDescent:
    status: str
    primary_domain_size: int
    giant_degree: int
    test_size: int
    certificate_count: int
    certificate_rank: int
    incidence_edges: int
    point_colors: tuple[int, ...]
    color_classes: tuple[tuple[int, ...], ...]
    largest_class: int
    significant_split: bool
    homogeneous_nontrivial_relation: bool
    refinement_rounds: int
    theorem_gate_certified: bool
    canonical_inputs_certified: bool
    exact_invariant: bool
    local_cost_certified: bool
    local_log2_cost_bound: float
    reason: str


def _fail(status, n, m, t, count, reason, *, gate=False, canonical=False):
    return CertificateIncidenceDescent(
        status, n, m, t, count, 0, 0, (), (), m, False, False, 0,
        gate, canonical, False, False, 0.0, reason,
    )


def certificate_incidence_descent(
    primary_domain_size: int,
    giant_degree: int,
    test_size: int,
    certificates: Iterable[tuple[Iterable[int], Hashable]],
    *,
    canonical_action_group: StabilizerChain,
    certificate_tokens_canonical: bool,
    max_class_fraction: float = 0.9,
    max_certificates: int = 200000,
    certificate_count_poly_power: int = 4,
) -> CertificateIncidenceDescent:
    """Aggregate proof-carrying local certificates into a canonical H5 descent.

    ``certificates`` is a colored t-uniform test family.  Unlike a caller-supplied
    Boolean claim of test-family canonicity, this routine mechanically verifies
    that the complete colored family is invariant under every generator of the
    supplied certified giant-domain action.  The certificate tokens themselves
    must come from an upstream canonical certificate construction; their claimed
    canonicity remains an explicit proof boundary rather than being inferred from
    arbitrary Python values.  The exact Babai local-certificate theorem parameter
    window is checked before any H5 progress is promoted.

    Stable 1-WL refinement of the colored point/test incidence graph then yields
    either a sufficiently balanced invariant point partition or, when the point
    side remains homogeneous but certificate colors are nontrivial, an exact
    higher-arity colored relation for the Design-Lemma-style branch.  All missing
    proof boundaries, theorem-window failures, size overflows and malformed input
    fail closed.

    The local accounting certificate is a conservative explicit operation bound
    on this aggregation only; it is not a claim that the remaining SI recurrence
    has been closed.
    """
    n = int(primary_domain_size)
    m = int(giant_degree)
    t = int(test_size)
    if n <= 0 or m <= 0 or t <= 0:
        return _fail("invalid_parameters", n, m, t, 0, "n, m and t must be positive")
    if not (0.0 < float(max_class_fraction) < 1.0):
        return _fail("invalid_split_fraction", n, m, t, 0, "max_class_fraction must lie in (0,1)")
    if max_certificates < 1 or certificate_count_poly_power < 1:
        return _fail("invalid_accounting_parameters", n, m, t, 0, "certificate limits must be positive")

    gate = babai_local_certificate_parameter_gate(n, m, t)
    if not gate.certified:
        return _fail(
            "theorem_parameter_gate_failed", n, m, t, 0,
            "local-certificate theorem parameter window is not certified: " + gate.reason,
        )
    if not certificate_tokens_canonical:
        return _fail(
            "uncertified_certificate_tokens", n, m, t, 0,
            "H5 aggregation requires upstream canonical certificate tokens",
            gate=True,
        )
    if canonical_action_group is None or canonical_action_group.degree != m:
        return _fail(
            "invalid_canonical_action_group", n, m, t, 0,
            "a certified permutation action of the full giant domain is required",
            gate=True,
        )

    rows = []
    seen = set()
    try:
        for raw_test, token in certificates:
            T = tuple(sorted(int(x) for x in raw_test))
            if len(T) != t or len(set(T)) != t or any(x < 0 or x >= m for x in T):
                return _fail(
                    "malformed_test_set", n, m, t, len(rows),
                    "every certificate test must be a distinct t-subset of the giant domain",
                    gate=True,
                )
            if T in seen:
                return _fail(
                    "duplicate_test_set", n, m, t, len(rows),
                    "a colored canonical test family may contain each test set at most once",
                    gate=True,
                )
            hash(token)
            seen.add(T)
            rows.append((T, token))
            if len(rows) > max_certificates:
                return _fail(
                    "certificate_limit_exceeded", n, m, t, len(rows),
                    "certificate family exceeds configured exact aggregation limit",
                    gate=True,
                )
    except (TypeError, ValueError):
        return _fail(
            "malformed_certificate_token", n, m, t, len(rows),
            "certificate tokens must be hashable canonical values and tests must contain integer points",
            gate=True,
        )

    count = len(rows)
    if count == 0:
        return _fail(
            "empty_certificate_family", n, m, t, 0,
            "no local certificates were supplied",
            gate=True,
        )
    if count > n ** certificate_count_poly_power:
        return _fail(
            "uncertified_certificate_count_cost", n, m, t, count,
            "certificate count exceeds configured polynomial local-work envelope",
            gate=True,
        )

    # Mechanical proof that the colored test family is invariant under the full
    # supplied action: checking a generating set suffices because preservation is
    # closed under composition and inverse.  This prevents an arbitrary sampled
    # family from being promoted merely because a caller labels it canonical.
    row_tokens = {T: token for T, token in rows}
    action_generators = canonical_action_group.original_generators or (identity(m),)
    missing = object()
    for g in action_generators:
        if len(g) != m or tuple(sorted(g)) != tuple(range(m)):
            return _fail(
                "malformed_canonical_action_generator", n, m, t, count,
                "canonical action contains a non-permutation generator",
                gate=True,
            )
        for T, token in rows:
            image = tuple(sorted(g[x] for x in T))
            if row_tokens.get(image, missing) != token:
                return _fail(
                    "colored_test_family_not_invariant", n, m, t, count,
                    "one canonical-action generator does not preserve the complete colored test family",
                    gate=True,
                )

    # Canonicalize certificate colors by token representation. Tokens are already
    # upstream-certified canonical and generator-equivariance was checked above;
    # repr only supplies deterministic internal color identifiers.
    token_keys = {token: (type(token).__qualname__, repr(token)) for _, token in rows}
    key_order = sorted(set(token_keys.values()))
    key_to_color = {key: i for i, key in enumerate(key_order)}
    test_colors = [key_to_color[token_keys[token]] for _, token in rows]
    certificate_rank = len(key_order)

    incident = [[] for _ in range(m)]
    for j, (T, _) in enumerate(rows):
        for x in T:
            incident[x].append(j)
    incidence_edges = count * t

    point_colors = [0] * m
    rounds = 0
    while True:
        point_signatures = []
        for x in range(m):
            counts = Counter(test_colors[j] for j in incident[x])
            point_signatures.append(("P", point_colors[x], tuple(sorted(counts.items()))))

        test_signatures = []
        for j, (T, _) in enumerate(rows):
            counts = Counter(point_colors[x] for x in T)
            test_signatures.append(("T", test_colors[j], tuple(sorted(counts.items()))))

        signatures = point_signatures + test_signatures
        labels = {sig: i for i, sig in enumerate(sorted(set(signatures), key=repr))}
        next_points = [labels[sig] for sig in point_signatures]
        next_tests = [labels[sig] for sig in test_signatures]
        rounds += 1
        if next_points == point_colors and next_tests == test_colors:
            break
        point_colors, test_colors = next_points, next_tests
        if rounds > m + count + 2:
            raise AssertionError("certificate incidence refinement failed to stabilize")

    classes = {}
    for x, color in enumerate(point_colors):
        classes.setdefault(color, []).append(x)
    color_classes = tuple(tuple(xs) for _, xs in sorted(classes.items()))
    largest = max((len(xs) for xs in color_classes), default=0)
    significant = len(color_classes) > 1 and largest <= float(max_class_fraction) * m + 1e-12
    homogeneous_relation = len(color_classes) == 1 and certificate_rank > 1

    work_units = max(1, rounds * (incidence_edges + m + count + 1) * (m + count + 1))
    local_log2 = log2(work_units)

    if significant:
        status = "certified_significant_point_split"
        reason = "mechanically action-invariant certificate incidence yields a balanced nontrivial point partition"
    elif homogeneous_relation:
        status = "certified_homogeneous_nontrivial_relation"
        reason = "point incidence remains homogeneous but the mechanically invariant certificate coloring defines a nontrivial higher-arity relation"
    elif len(color_classes) > 1:
        status = "canonical_nonsignificant_point_partition"
        reason = "canonical incidence refinement splits points, but the largest class does not satisfy the configured significant-split bound"
    else:
        status = "certificate_relation_trivial"
        reason = "certificate incidence remains point-homogeneous and carries only one certificate color"

    return CertificateIncidenceDescent(
        status, n, m, t, count, certificate_rank, incidence_edges,
        tuple(point_colors), color_classes, largest, significant,
        homogeneous_relation, rounds, True, True, True, True,
        local_log2, reason,
    )
