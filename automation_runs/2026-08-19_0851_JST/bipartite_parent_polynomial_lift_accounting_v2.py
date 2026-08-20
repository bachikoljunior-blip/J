from __future__ import annotations

import bipartite_parent_action_coset_intersection_v1 as _parent_intersection
import bipartite_parent_polynomial_lift_accounting_v1 as _core
from bipartite_parent_polynomial_lift_accounting_v1 import (
    BipartiteParentPolynomialLiftCertificate,
    PolynomialLiftBranchCertificate,
)
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from u2_candidate_coset_string_iso_v5 import candidate_coset_string_isomorphism_u5


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
    """Replay-stable rev207 entry point through the rev210 candidate closure.

    rev207 intentionally reuses the same structural inputs twice: first for the
    complete rev206 parent union and then for proof-tree replay of every exact
    image child.  Materialize every user-supplied iterable exactly once here so a
    generator/iterator cannot be silently exhausted between those two phases.

    rev208 added exact literal natural A_n/S_n SI and rev209 added whole-candidate
    acceptance plus the larger-Johnson log/Design bridge.  rev210 advances the
    same shared dispatcher to v5, which closes multiple equally canonical minimum
    block systems by processing the complete canonical family and requiring exact
    quotient/preimage consensus.  The recurrence verifier is advanced to v4 so an
    exact same-domain quotient fiber may terminate directly while every genuinely
    recursive quotient fiber must still expose strict kernel-orbit shrink.

    Both rev206 execution and rev207 replay use the same v5 dispatcher and v4
    validator, preserving status/accounting correspondence rather than post-hoc
    certification.
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

    _core.candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u5
    _parent_intersection.candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u5
    _core.validate_quasipoly_recurrence_tree_v3 = validate_quasipoly_recurrence_tree_v4

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
