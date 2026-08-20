from __future__ import annotations

from bipartite_parent_polynomial_lift_accounting_v1 import (
    BipartiteParentPolynomialLiftCertificate,
    PolynomialLiftBranchCertificate,
    solve_and_certify_design_parent_polynomial_lift as _solve_v1,
)


def solve_and_certify_design_parent_polynomial_lift(
    parent_group,
    right_image_generators,
    left_points,
    right_points,
    source_edges,
    target_edges,
    *,
    source_left_colors=None,
    target_left_colors=None,
    source_right_colors=None,
    target_right_colors=None,
    **kwargs,
):
    """Replay-stable rev207 entry point.

    rev207 intentionally reuses the same structural inputs twice: first for the
    complete rev206 parent union and then for proof-tree replay of every exact
    image child.  Materialize every user-supplied iterable exactly once here so a
    generator/iterator cannot be silently exhausted between those two phases.
    The v1 core is otherwise unchanged and remains fail-closed.
    """
    right_image_generators = tuple(right_image_generators)
    left_points = tuple(left_points)
    right_points = tuple(right_points)
    source_edges = tuple(source_edges)
    target_edges = tuple(target_edges)
    source_left_colors = None if source_left_colors is None else tuple(source_left_colors)
    target_left_colors = None if target_left_colors is None else tuple(target_left_colors)
    source_right_colors = None if source_right_colors is None else tuple(source_right_colors)
    target_right_colors = None if target_right_colors is None else tuple(target_right_colors)
    return _solve_v1(
        parent_group,
        right_image_generators,
        left_points,
        right_points,
        source_edges,
        target_edges,
        source_left_colors=source_left_colors,
        target_left_colors=target_left_colors,
        source_right_colors=source_right_colors,
        target_right_colors=target_right_colors,
        **kwargs,
    )


__all__ = [
    "PolynomialLiftBranchCertificate",
    "BipartiteParentPolynomialLiftCertificate",
    "solve_and_certify_design_parent_polynomial_lift",
]
