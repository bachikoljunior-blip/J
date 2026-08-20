from __future__ import annotations

from permutation_group_schreier import inverse
from signed_johnson_ground_relational_si_v1 import signed_johnson_ground_relational_small_order_terminal
from signed_johnson_log_certificate_design_descent_si_v1 import signed_johnson_log_certificate_design_descent_si
from u2_candidate_coset_string_iso_v2 import _translate_subgroup_si_back_to_candidate
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3


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
    """U3 plus existing large-ground Johnson exact paths.

    The old U2 primitive-non-giant branch already recognized small-ground Johnson
    actions but stopped when the certified Johnson ground exceeded its explicit
    brute-force window.  rev176 and rev184 later added two strictly stronger
    current-J substrates that were never wired back into this candidate boundary:

      * faithful signed-ground exact SI when the represented signed group is small;
      * logarithmic relation/Design descent, which can itself prove exact emptiness
        or an exact filtered candidate solve without giant-group enumeration.

    rev209 reuses those substrates only after U3 has exhausted every previously
    exact path.  Source coordinates are shifted into H for the right candidate
    H*r, and every exact subgroup result is translated back through the existing
    right-coset translation primitive.  Nonexact structural evidence is not
    promoted to an exact parent claim.
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
    if first.exact:
        return first

    # These are the primitive-non-giant statuses for which a Johnson relational
    # lift can be a strict improvement.  Other unresolved structural classes stay
    # owned by their existing operators.
    if first.status not in {
        "undetermined_johnson_ground_cap",
        "undetermined_primitive_non_giant_not_johnson",
        "undetermined_primitive_non_giant",
    }:
        return first

    n = candidate.subgroup.degree
    r = candidate.representative
    rinv = inverse(r)
    subgroup_source = tuple(source[rinv[j]] for j in range(n))

    signed = signed_johnson_ground_relational_small_order_terminal(
        candidate.subgroup,
        subgroup_source,
        target,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_signed_ground_group_order,
        max_recognition_nodes=max_recognition_nodes,
    )
    if signed.exact:
        return _translate_subgroup_si_back_to_candidate(signed, r, degree=n)

    log_design = signed_johnson_log_certificate_design_descent_si(
        candidate.subgroup,
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


__all__ = ["candidate_coset_string_isomorphism_u4"]
