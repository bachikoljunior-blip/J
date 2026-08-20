from __future__ import annotations

from permutation_group_schreier import inverse
from signed_johnson_ground_relational_si_v1 import signed_johnson_ground_relational_small_order_terminal
from signed_johnson_log_certificate_design_descent_si_v1 import signed_johnson_log_certificate_design_descent_si
from u2_candidate_coset_string_iso_v2 import _translate_subgroup_si_back_to_candidate
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3


_PRIMITIVE_JOHNSON_REMAINDER = {
    "undetermined_johnson_ground_cap",
    "undetermined_primitive_non_giant_not_johnson",
    "undetermined_primitive_non_giant",
}


def candidate_coset_string_isomorphism_u4(
    candidate,
    source_values,
    target_values,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_signed_ground_group_order: int = 4096,
    max_recognition_nodes: int = 500000,
    max_test_sets: int = 200000,
    max_partition_states: int = 4096,
    max_depth: int = 64,
):
    """rev211: continue only the exact Johnson remainder left by candidate-v3.

    rev209 already routes a certified primitive Johnson candidate through joint
    lower-arity relations, the adaptive single-relation image and the exact
    profile-determined terminal.  If all of those exact routes fail, two older
    proof-carrying substrates remain stronger than the legacy ground-size cap:

    * rev176 can solve the complete colored Johnson relation exactly when the
      *represented* faithful signed-ground group has polynomially bounded order;
    * rev184 can form a canonical O(log n)-arity relation and may prove exact
      emptiness or an exact candidate solve after a certified significant split.

    This wrapper invokes those substrates only for typed primitive/Johnson
    remainder statuses.  It strips the fixed representative of H*r before the
    subgroup calculation and translates back only exact results.  Structural
    filters and theorem evidence from rev184 stay nonexact and are never promoted
    to a parent String-Isomorphism answer.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    first = candidate_coset_string_isomorphism_u3(
        candidate,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
    )
    if first.exact or first.status not in _PRIMITIVE_JOHNSON_REMAINDER:
        return first

    H = candidate.subgroup
    n = H.degree
    r = candidate.representative
    rinv = inverse(r)
    subgroup_source = tuple(source[rinv[j]] for j in range(n))

    signed = signed_johnson_ground_relational_small_order_terminal(
        H,
        subgroup_source,
        target,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_signed_ground_group_order,
        max_recognition_nodes=max_recognition_nodes,
    )
    if signed.exact:
        return _translate_subgroup_si_back_to_candidate(signed, r, degree=n)

    # A failed exact Johnson lift is common to both rev176 and rev184.  Do not
    # repeat the bounded recognizer when rev176 has already certified that this
    # candidate is not an exact relational Johnson lift.
    if signed.status == "undetermined_signed_johnson_ground_lift":
        return first

    log_design = signed_johnson_log_certificate_design_descent_si(
        H,
        subgroup_source,
        target,
        root_n=root_n,
        max_test_sets=max_test_sets,
        max_recognition_nodes=max_recognition_nodes,
        max_partition_states=max_partition_states,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        candidate_group_order_poly_power=group_order_poly_power,
        max_candidate_group_order=max_group_order,
        max_depth=max_depth,
    )
    if log_design.exact:
        return _translate_subgroup_si_back_to_candidate(log_design, r, degree=n)

    return first


candidate_coset_string_isomorphism_u2 = candidate_coset_string_isomorphism_u4


__all__ = ["candidate_coset_string_isomorphism_u4", "candidate_coset_string_isomorphism_u2"]
