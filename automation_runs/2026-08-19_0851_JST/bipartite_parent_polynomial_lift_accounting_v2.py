from __future__ import annotations

import bipartite_parent_action_coset_intersection_v1 as _parent_intersection
import bipartite_parent_polynomial_lift_accounting_v1 as _core
from bipartite_parent_polynomial_lift_accounting_v1 import (
    BipartiteParentPolynomialLiftCertificate,
    PolynomialLiftBranchCertificate,
)
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from u2_candidate_coset_string_iso_v7 import candidate_coset_string_isomorphism_u7


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
    """Replay-stable rev207 entry point through the rev214 pair-image closure.

    rev207 originally reused the same structural inputs twice: first for the
    complete rev206 parent union and then for proof-tree replay of every exact
    image child.  rev218 removes that duplicate solver execution: rev206 captures
    the immutable image proof actually produced, and polynomial-lift accounting
    consumes that same object.  Inputs remain materialized once so one-shot
    iterables have execution-stable identity.

    rev208 added exact literal natural A_n/S_n SI; rev209 added whole-candidate
    acceptance plus the larger-Johnson log/Design bridge; rev210 closed multiple
    equally canonical minimum block systems by family-wide exact consensus.
    rev211 advances the same shared dispatcher to v6: when rev184's logarithmic
    codegree descent reaches the exact second-Johnson structural leaf, the actual
    canonical pair relation is solved in its induced action, lifted by exact
    paired-action preimage, and the original full string is solved inside that
    filter.  No arbitrary second-ground coordinate representative is selected.

    rev212 reconnects the already validated rev177 Johnson ground-profile exact
    terminal at both the direct candidate and S1 orbit-child boundaries.  This
    closes profile-determined larger Johnson actions and exact profile mismatch
    without group enumeration; profile partition resource caps stay fail closed.

    rev213 makes that significant-profile filter usable at nested orbit depth:
    S1 recursively preserves its newest terminals, sends transitive imprimitive
    children back through the existing candidate block/family dispatcher, and
    reuses the bounded-ground Johnson terminal inside the explicit auxiliary
    window.  rev177 source stabilizers are conjugated to the target side required
    by the repository's right-coset convention, including odd-parity witnesses.

    rev214 removes an unnecessary Johnson-only gate after logarithmic codegree
    descent: every nonconstant pair relation with C(v,2)<C(v,k) is solved in its
    exact induced action and lifted back by the same paired preimage machinery.
    Homogeneous, nonshrinking, nonrestricting, and resource-capped images remain
    fail closed, with nonrestricting candidates barred from same-domain recursion.

    The recurrence verifier remains v4: exact same-domain quotient fibers may
    terminate directly, while every genuinely recursive quotient fiber must expose
    strict kernel-orbit shrink.  rev206 execution uses the v7 dispatcher and
    captures its exact proof; rev207 accounting validates that same object with
    v4, preserving execution/status/accounting correspondence rather than post-hoc
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

    _core.candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u7
    _parent_intersection.candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u7
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
