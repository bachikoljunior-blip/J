from __future__ import annotations

from collections import Counter
from dataclasses import replace
from itertools import combinations
from math import ceil, comb, log2

import signed_johnson_log_certificate_design_descent_si_v1 as _base
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from signed_johnson_complement_safe_image_si_v1 import complement_safe_t_relation_signatures
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from upcc_subconstituent_full_string_si_v1 import upcc_subconstituent_full_string_isomorphism


def _exact_upcc_from_relation(
    group,
    lifted_generators,
    v,
    t,
    source_relation,
    target_relation,
    source_values,
    target_values,
    *,
    root_n,
    max_tuple_states=250000,
    max_twl_rounds=None,
    max_twl_work_units=100000000,
    max_partition_pair_branches=200000,
    max_partition_states=200000,
    polylog_power=2,
    max_explicit_degree=8,
    candidate_group_order_poly_power=2,
    max_candidate_group_order=256,
    max_depth=64,
):
    """Try the already-proved rev197/rev198 UPCC child on one exact t-relation.

    This helper is deliberately an exactness bridge, not a new theorem.  It reuses
    the stable exact k-WL UPCC classifier, complete all-root subconstituent split
    family, exact ambient partition transport, and exact full-string branch union.
    If the relation is not the certified full-ground UPCC case, or any materialized
    cover exceeds its cap, the existing fail-closed result is returned unchanged.
    """
    return upcc_subconstituent_full_string_isomorphism(
        group,
        lifted_generators,
        int(v),
        int(t),
        tuple(source_relation),
        tuple(target_relation),
        tuple(source_values),
        tuple(target_values),
        root_n=int(root_n),
        max_tuple_states=max_tuple_states,
        max_twl_rounds=max_twl_rounds,
        max_twl_work_units=max_twl_work_units,
        max_partition_pair_branches=max_partition_pair_branches,
        max_partition_states=max_partition_states,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=candidate_group_order_poly_power,
        max_group_order=max_candidate_group_order,
        max_depth=max_depth,
    )


def signed_johnson_log_certificate_design_descent_si_v2(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    max_class_fraction: float = 0.9,
    max_test_sets: int = 200000,
    max_recognition_nodes: int = 500000,
    max_johnson_nodes: int = 500000,
    partition_state_poly_power: int = 2,
    max_partition_states: int = 4096,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
    max_depth: int = 64,
    max_upcc_tuple_states: int = 250000,
    max_upcc_twl_rounds: int | None = None,
    max_upcc_twl_work_units: int = 100000000,
    max_upcc_partition_pair_branches: int = 200000,
):
    """rev210 cross-cut: send the homogeneous log-relation remainder to rev198 UPCC.

    rev184 already constructs an exact canonical logarithmic t-subset relation on
    the recognized Johnson ground and closes invariant, point-split and lower-
    arity Johnson cases.  Its final homogeneous Design remainder was historically
    left unresolved.  rev193/rev197/rev198 later implemented a stronger exact path
    for one important subcase of exactly that representation: a full-ground UPCC
    under stable exact t-WL whose every rooted subconstituent partition alpha-
    shrinks.  This wrapper reuses that later solver rather than maintaining two
    parallel problem branches.

    Exact UPCC set closure is exposed immediately.  The rev198 implementation
    explicitly did not certify the global theorem-scale recurrence, so this wrapper
    also does not invent one: the returned exact coset has local_cost_certified
    false and carries an uncertified accounting leaf.  Thus it deletes the set-
    exactness child while leaving recurrence certification as the next obligation.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if root_n is None:
        root_n = n

    base = _base.signed_johnson_log_certificate_design_descent_si(
        group,
        source,
        target,
        root_n=root_n,
        max_class_fraction=max_class_fraction,
        max_test_sets=max_test_sets,
        max_recognition_nodes=max_recognition_nodes,
        max_johnson_nodes=max_johnson_nodes,
        partition_state_poly_power=partition_state_poly_power,
        max_partition_states=max_partition_states,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        candidate_group_order_poly_power=candidate_group_order_poly_power,
        max_candidate_group_order=max_candidate_group_order,
        max_depth=max_depth,
    )
    if base.exact or base.status != "undetermined_log_certificate_design_gate":
        return base

    lift = lift_primitive_johnson_to_ground_relation(
        group, source, target, max_recognition_nodes=max_recognition_nodes
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    if v < 1 or k <= 2:
        return base
    arity_cap = max(1, ceil(log2(max(2, v))))
    t = min(k - 1, max(2, arity_cap))
    test_count = comb(v, t)
    if t > arity_cap or test_count > max_test_sets:
        return base

    complement = any(bool(g.complement) for g in lift.lifted_generators)
    source_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    target_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)
    source_relation = complement_safe_t_relation_signatures(
        v, k, source_tokens, t, complement_in_image=complement
    )
    target_relation = complement_safe_t_relation_signatures(
        v, k, target_tokens, t, complement_in_image=complement
    )
    if Counter(source_relation) != Counter(target_relation):
        # rev184 already handles this terminal; retaining the base result here
        # prevents the wrapper from becoming a second invariant implementation.
        return base

    upcc = _exact_upcc_from_relation(
        group,
        lift.lifted_generators,
        v,
        t,
        source_relation,
        target_relation,
        source,
        target,
        root_n=root_n,
        max_tuple_states=max_upcc_tuple_states,
        max_twl_rounds=max_upcc_twl_rounds,
        max_twl_work_units=max_upcc_twl_work_units,
        max_partition_pair_branches=max_upcc_partition_pair_branches,
        max_partition_states=max_partition_states,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        candidate_group_order_poly_power=candidate_group_order_poly_power,
        max_candidate_group_order=max_candidate_group_order,
        max_depth=max_depth,
    )
    if not upcc.exact:
        return base

    coset = None
    if upcc.full_string_result is not None:
        coset = upcc.full_string_result.coset
    bound = float(upcc.local_log2_cost_bound)
    accounting = RecurrenceAccountingNode(
        n=int(root_n),
        m=max(1, v),
        operation_kind="exact_log_relation_upcc_full_string_unaccounted",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=(),
        terminal_certified=True,
        reason=(
            "rev198 exact full-ground UPCC subconstituent cover closed the set-valued SI child; "
            "global recurrence charge for this reused branch family is intentionally still uncertified"
        ),
    )
    return replace(
        base,
        status=(
            "exact_empty_log_relation_upcc_full_string"
            if coset is None
            else "exact_log_relation_upcc_full_string_coset"
        ),
        coset=coset,
        operation_kind="log_relation_upcc_full_string",
        exact=True,
        local_cost_certified=False,
        local_log2_cost_bound=bound,
        terminal_certified=True,
        children=(),
        accounting=accounting,
        permutation_candidates_checked=(
            base.permutation_candidates_checked + int(upcc.partition_pair_count)
        ),
        reason=(
            "the rev184 homogeneous logarithmic relation is a rev197/rev198 certified full-ground UPCC; "
            "its complete all-root subconstituent cover and exact full-string union close this SI set, "
            "while theorem-scale recurrence accounting remains open"
        ),
    )


signed_johnson_log_certificate_design_descent_si = signed_johnson_log_certificate_design_descent_si_v2

__all__ = [
    "_exact_upcc_from_relation",
    "signed_johnson_log_certificate_design_descent_si_v2",
    "signed_johnson_log_certificate_design_descent_si",
]
