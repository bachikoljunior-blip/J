from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from canonical_cartesian_block_family_v1 import certify_canonical_cartesian_block_family
from cartesian_block_family_action_v1 import exact_cartesian_block_family_action
from s1_string_isomorphism_v2 import s1_string_isomorphism_v2


@dataclass(frozen=True)
class CartesianStringMarginalFilter:
    status: str
    original_degree: int
    reduced_degree: int
    exact_empty: bool
    reduced_exact: bool
    reduced_candidate_nonempty: bool
    source_coordinate_colors: tuple
    target_coordinate_colors: tuple
    reduced_proof: object | None
    reason: str


def _block_histogram(values, block):
    try:
        return frozenset(Counter(values[u] for u in block).items())
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc


def cartesian_string_marginal_filter(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    max_group_order: int = 4096,
) -> CartesianStringMarginalFilter:
    """Use Cartesian factor-block histograms as an exact-empty SI filter.

    Every original string isomorphism maps each canonical factor block to a block
    with the same multiset of values.  Therefore it induces a String-Isomorphism
    of the histogram-colored coordinate-block domain under the faithful reduced
    group action.  If that reduced SI set is exactly empty, the original SI set
    is exactly empty.  A nonempty reduced result is only a necessary candidate
    and is deliberately not promoted to an original-domain solution until an
    exact relational lift/refinement operator is available.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    family = certify_canonical_cartesian_block_family(group)
    action = exact_cartesian_block_family_action(group)
    if not family.exact_cartesian or not action.faithful or action.image is None:
        return CartesianStringMarginalFilter(
            "cartesian_marginal_filter_unavailable",
            n,
            0,
            False,
            False,
            False,
            (),
            (),
            None,
            "the canonical minimum block family is not an exact faithful Cartesian coordinate action",
        )

    blocks = tuple(block for system in family.block_system_family for block in system)
    source_colors = tuple(_block_histogram(source, block) for block in blocks)
    target_colors = tuple(_block_histogram(target, block) for block in blocks)
    reduced = s1_string_isomorphism_v2(
        action.image,
        source_colors,
        target_colors,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        max_group_order=max_group_order,
    )

    if reduced.exact and reduced.coset is None:
        return CartesianStringMarginalFilter(
            "exact_empty_cartesian_marginal",
            n,
            action.reduced_degree,
            True,
            True,
            False,
            source_colors,
            target_colors,
            reduced,
            "the faithful reduced coordinate action has no permutation mapping source factor-block value histograms to target histograms; every original SI would induce one, so the original SI set is empty",
        )
    if reduced.exact and reduced.coset is not None:
        return CartesianStringMarginalFilter(
            "cartesian_marginal_candidate_requires_exact_lift",
            n,
            action.reduced_degree,
            False,
            True,
            True,
            source_colors,
            target_colors,
            reduced,
            "factor-block marginals admit a reduced exact candidate coset, but marginals are only necessary invariants; original cell-label compatibility still requires exact relational lift/refinement",
        )
    return CartesianStringMarginalFilter(
        "cartesian_marginal_reduced_child_unresolved",
        n,
        action.reduced_degree,
        False,
        False,
        False,
        source_colors,
        target_colors,
        reduced,
        "the reduced coordinate-block String-Isomorphism child is itself unresolved; no original-domain conclusion is made",
    )
