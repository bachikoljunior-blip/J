from __future__ import annotations

import bipartite_parent_action_coset_intersection_v1 as _parent_intersection
import bipartite_parent_polynomial_lift_accounting_v1 as _core
from bipartite_parent_polynomial_lift_accounting_v1 import (
    BipartiteParentPolynomialLiftCertificate,
    PolynomialLiftBranchCertificate,
)
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3


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
    """Replay-stable rev207 entry point plus the rev208 literal-giant closure.

    rev207 intentionally reuses the same structural inputs twice: first for the
    complete rev206 parent union and then for proof-tree replay of every exact
    image child.  Materialize every user-supplied iterable exactly once here so a
    generator/iterator cannot be silently exhausted between those two phases.

    rev208 additionally replaces only the candidate-SI dispatch used by both the
    rev206 parent intersection and rev207 proof replay with v3.  v3 closes literal
    natural A_n/S_n fibers by exact color-class transport and delegates every
    other structural state unchanged to v2.  Patching both module globals keeps
    union execution and replay on the same solver, so status equality remains an
    execution-linked invariant rather than a post-hoc accounting fiction.
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

    _core.candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u3
    _parent_intersection.candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u3

    return _core.solve_and_certify_design_parent_polynomial_lift(
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
