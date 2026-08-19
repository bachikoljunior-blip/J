from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import ceil, comb, log2

from babai_recurrence_contract_v1 import (
    RecurrenceCertificate,
    RecurrenceChild,
    RecurrenceValidation,
    validate_babai_recurrence_step,
)
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from signed_johnson_complement_safe_image_si_v1 import (
    complement_safe_t_relation_signatures,
)
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_relation_arity_selector_v1 import (
    choose_complement_safe_relation_arity,
)


@dataclass(frozen=True)
class GuidePartitionOutcome:
    guide: tuple[int, ...]
    fingerprint: tuple
    partition_cells: tuple[int, ...]
    largest_cell: int
    significant_split: bool


@dataclass(frozen=True)
class LocalGuidePartitionPlan:
    status: str
    ground_size: int
    relation_arity: int
    guide_size: int
    source_outcomes: tuple[GuidePartitionOutcome, ...]
    target_outcomes: tuple[GuidePartitionOutcome, ...]
    compatible_guide_pairs: int
    recurrence: RecurrenceCertificate | None
    recurrence_validation: RecurrenceValidation | None
    quasipolynomial_guide_bound_verified: bool
    reason: str


def _point_histogram_partition(v: int, relation_arity: int, relation_colors, guide):
    r = int(relation_arity)
    A = tuple(sorted(int(x) for x in guide))
    if len(A) != r - 2:
        raise ValueError("guide size must equal relation_arity - 2")
    if len(set(A)) != len(A) or any(x < 0 or x >= v for x in A):
        raise ValueError("invalid guide")

    coords = tuple(combinations(range(v), r))
    colors = tuple(relation_colors)
    if len(colors) != len(coords):
        raise ValueError("relation color count does not match the r-subset domain")
    color_of = {coord: colors[i] for i, coord in enumerate(coords)}
    residual = tuple(x for x in range(v) if x not in set(A))

    point_signature = {}
    for x in residual:
        hist = Counter(
            color_of[tuple(sorted(A + (x, y)))]
            for y in residual
            if y != x
        )
        point_signature[x] = tuple(sorted(hist.items(), key=repr))

    classes = defaultdict(list)
    for x in residual:
        classes[point_signature[x]].append(x)
    residual_cells = tuple(
        tuple(xs)
        for _, xs in sorted(classes.items(), key=lambda item: repr(item[0]))
    )
    cell_sizes = tuple(sorted((len(cell) for cell in residual_cells), reverse=True))
    # The guide is individualized: each guide point is its own singleton cell.
    partition_cells = tuple(sorted(cell_sizes + (1,) * len(A), reverse=True))
    largest = max(partition_cells, default=0)
    fingerprint = tuple(
        sorted(
            ((sig, len(xs)) for sig, xs in classes.items()),
            key=repr,
        )
    )
    return fingerprint, partition_cells, largest


def build_local_guide_partition_plan(
    v: int,
    relation_arity: int,
    source_relation_colors,
    target_relation_colors,
    *,
    root_n: int,
    max_class_fraction: float = 0.9,
    guide_log_power: int = 1,
):
    """Build an exhaustive, label-invariant guide-branch recurrence plan.

    For an r-subset colored relation, every (r-2)-subset A is an individualized
    local guide.  On the residual points, x is colored by the exact histogram of
    colors of r-sets A union {x,y} as y varies.  This is a canonical partition
    *relative to A*.  Instead of choosing a label-dependent guide, we include the
    complete guide family.  Under an isomorphism, guides and their point-histogram
    fingerprints are transported bijectively, so branching over all compatible
    source/target guide pairs is an exact invariant family.

    If a guide yields a significant partition, the recursive child measure is its
    largest cell after guide points are individualized.  The branch family is
    quasipolynomially bounded when g=r-2 <= (log2 root_n)^guide_log_power: there
    are at most C(v,g)^2 <= root_n^(2g) source/target guide pairs.  This function
    certifies that local recurrence obligation only.  Executing the guide-pair
    transporter cosets and full string children remains a separate leaf.
    """
    v = int(v)
    r = int(relation_arity)
    root_n = int(root_n)
    if v < 3 or root_n < v:
        raise ValueError("root_n must dominate a ground of size at least three")
    if not (3 <= r <= v):
        raise ValueError("relation_arity must be at least three")
    if not (0.5 < max_class_fraction < 1.0):
        raise ValueError("max_class_fraction must lie in (0.5,1)")
    if guide_log_power < 1:
        raise ValueError("guide_log_power must be positive")

    g = r - 2
    guides = tuple(combinations(range(v), g))
    source_colors = tuple(source_relation_colors)
    target_colors = tuple(target_relation_colors)
    if len(source_colors) != comb(v, r) or len(target_colors) != comb(v, r):
        raise ValueError("relation color count does not match C(v,r)")

    def outcomes(colors):
        out = []
        for A in guides:
            fingerprint, cells, largest = _point_histogram_partition(v, r, colors, A)
            significant = len(cells) > g + 1 and largest <= max_class_fraction * v + 1e-12
            out.append(GuidePartitionOutcome(A, fingerprint, cells, largest, significant))
        return tuple(out)

    src = outcomes(source_colors)
    dst = outcomes(target_colors)
    src_good = tuple(x for x in src if x.significant_split)
    dst_good = tuple(x for x in dst if x.significant_split)

    # Compatibility uses the exact histogram fingerprint, not merely cell sizes.
    # A true ground isomorphism mapping A to B preserves this fingerprint.
    dst_by_fp = Counter(x.fingerprint for x in dst_good)
    compatible = sum(dst_by_fp[x.fingerprint] for x in src_good)

    log_cap = ceil(log2(max(2, root_n))) ** guide_log_power
    quasipoly_gate = bool(g <= log_cap and len(guides) ** 2 <= root_n ** (2 * max(1, g)))

    if not src_good and not dst_good:
        return LocalGuidePartitionPlan(
            "no_significant_local_guide_partition", v, r, g, src, dst, 0,
            None, None, quasipoly_gate,
            "every individualized guide leaves one residual point-histogram cell too large; this guide statistic is exhausted",
        )
    if compatible == 0:
        return LocalGuidePartitionPlan(
            "exact_empty_local_guide_fingerprint_invariant", v, r, g, src, dst, 0,
            None, None, quasipoly_gate,
            "source has a significant guide fingerprint with no compatible target guide (or conversely); no ground permutation can be an isomorphism",
        )

    grouped = Counter()
    for s in src_good:
        matches = dst_by_fp[s.fingerprint]
        if matches:
            grouped[(s.largest_cell, s.partition_cells)] += matches
    children = tuple(
        RecurrenceChild(domain_size=largest, multiplicity=mult, canonical_partition_cells=cells)
        for (largest, cells), mult in sorted(grouped.items())
    )
    cert = RecurrenceCertificate(
        parent_domain_size=v,
        children=children,
        progress_kind="exhaustive_local_guide_point_histogram_partition",
        local_certificate_count=len(src) + len(dst),
        canonical=True,
        complexity_charge=ceil(log2(max(2, len(guides) ** 2))),
        reason="complete compatible guide-pair family; every child individualizes the guide and recurses only on a significantly smaller canonical point cell",
    )
    validation = validate_babai_recurrence_step(
        cert,
        max_branch_factor=max(1, len(guides) ** 2),
        min_shrink_fraction=max(0.01, 1.0 - max_class_fraction),
    )
    status = (
        "verified_quasipoly_local_guide_partition_plan"
        if validation.progress_verified and quasipoly_gate
        else "verified_local_guide_partition_plan_without_theorem_scale_gate"
        if validation.progress_verified
        else "invalid_local_guide_partition_plan"
    )
    return LocalGuidePartitionPlan(
        status, v, r, g, src, dst, compatible, cert, validation,
        quasipoly_gate,
        validation.reason,
    )


def adaptive_signed_johnson_local_guide_plan(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    relation_arity: int | None = None,
    max_relation_arity: int | None = None,
    max_recognition_nodes: int = 500000,
    max_class_fraction: float = 0.9,
    guide_log_power: int = 1,
):
    """Construct a rev184 guide recurrence plan from the certified Johnson lift."""
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    lift = lift_primitive_johnson_to_ground_relation(
        group, source, target, max_recognition_nodes=max_recognition_nodes
    )
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        return LocalGuidePartitionPlan(
            "undetermined_local_guide_johnson_lift", int(lift.ground_size),
            int(relation_arity or 0), max(0, int(relation_arity or 2) - 2),
            (), (), 0, None, None, False, lift.reason,
        )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    complement = any(bool(g.complement) for g in lift.lifted_generators)
    src_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    dst_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)

    if relation_arity is None:
        choice = choose_complement_safe_relation_arity(
            v, k, src_tokens, dst_tokens,
            complement_in_image=complement,
            max_arity=max_relation_arity,
        )
        if choice.arity is None or choice.arity < 3:
            return LocalGuidePartitionPlan(
                "undetermined_no_higher_arity_guide_relation", v,
                int(choice.arity or 0), max(0, int(choice.arity or 2) - 2),
                (), (), 0, None, None, False,
                choice.reason + "; a guide partition requires a selected relation arity of at least three",
            )
        relation_arity = choice.arity

    r = int(relation_arity)
    src_relation = complement_safe_t_relation_signatures(
        v, k, src_tokens, r, complement_in_image=complement
    )
    dst_relation = complement_safe_t_relation_signatures(
        v, k, dst_tokens, r, complement_in_image=complement
    )
    return build_local_guide_partition_plan(
        v, r, src_relation, dst_relation,
        root_n=root_n,
        max_class_fraction=max_class_fraction,
        guide_log_power=guide_log_power,
    )
