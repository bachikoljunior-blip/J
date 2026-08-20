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


def _exact_upcc_from_relation(group, lifted_generators, v, t, source_relation, target_relation, source_values, target_values, *, root_n, max_tuple_states=250000, max_twl_rounds=None, max_twl_work_units=100000000, max_partition_pair_branches=200000, max_partition_states=200000, polylog_power=2, max_explicit_degree=8, candidate_group_order_poly_power=2, max_candidate_group_order=256, max_depth=64):
    return upcc_subconstituent_full_string_isomorphism(group, lifted_generators, int(v), int(t), tuple(source_relation), tuple(target_relation), tuple(source_values), tuple(target_values), root_n=int(root_n), max_tuple_states=max_tuple_states, max_twl_rounds=max_twl_rounds, max_twl_work_units=max_twl_work_units, max_partition_pair_branches=max_partition_pair_branches, max_partition_states=max_partition_states, polylog_power=polylog_power, max_explicit_degree=max_explicit_degree, group_order_poly_power=candidate_group_order_poly_power, max_group_order=max_candidate_group_order, max_depth=max_depth)


def signed_johnson_log_certificate_design_descent_si_v2(group, source_values, target_values, *, root_n=None, max_class_fraction=0.9, max_test_sets=200000, max_recognition_nodes=500000, max_johnson_nodes=500000, partition_state_poly_power=2, max_partition_states=4096, polylog_power=2, max_explicit_degree=8, candidate_group_order_poly_power=2, max_candidate_group_order=256, max_depth=64, max_upcc_tuple_states=250000, max_upcc_twl_rounds=None, max_upcc_twl_work_units=100000000, max_upcc_partition_pair_branches=200000):
    source, target = tuple(source_values), tuple(target_values)
    n = group.degree
    if root_n is None: root_n = n
    base = _base.signed_johnson_log_certificate_design_descent_si(group, source, target, root_n=root_n, max_class_fraction=max_class_fraction, max_test_sets=max_test_sets, max_recognition_nodes=max_recognition_nodes, max_johnson_nodes=max_johnson_nodes, partition_state_poly_power=partition_state_poly_power, max_partition_states=max_partition_states, polylog_power=polylog_power, max_explicit_degree=max_explicit_degree, candidate_group_order_poly_power=candidate_group_order_poly_power, max_candidate_group_order=max_candidate_group_order, max_depth=max_depth)
    if base.exact or base.status != "undetermined_log_certificate_design_gate": return base
    lift = lift_primitive_johnson_to_ground_relation(group, source, target, max_recognition_nodes=max_recognition_nodes)
    v, k = int(lift.ground_size), int(lift.subset_size)
    if v < 1 or k <= 2: return base
    arity_cap = max(1, ceil(log2(max(2, v))))
    t = min(k - 1, max(2, arity_cap))
    if t > arity_cap or comb(v, t) > max_test_sets: return base
    complement = any(bool(g.complement) for g in lift.lifted_generators)
    s = complement_safe_t_relation_signatures(v, k, tuple(_color_token(x) for x in lift.source_on_standard_subsets), t, complement_in_image=complement)
    d = complement_safe_t_relation_signatures(v, k, tuple(_color_token(x) for x in lift.target_on_standard_subsets), t, complement_in_image=complement)
    if Counter(s) != Counter(d): return base
    upcc = _exact_upcc_from_relation(group, lift.lifted_generators, v, t, s, d, source, target, root_n=root_n, max_tuple_states=max_upcc_tuple_states, max_twl_rounds=max_upcc_twl_rounds, max_twl_work_units=max_upcc_twl_work_units, max_partition_pair_branches=max_upcc_partition_pair_branches, max_partition_states=max_partition_states, polylog_power=polylog_power, max_explicit_degree=max_explicit_degree, candidate_group_order_poly_power=candidate_group_order_poly_power, max_candidate_group_order=max_candidate_group_order, max_depth=max_depth)
    if not upcc.exact: return base
    coset = upcc.full_string_result.coset if upcc.full_string_result is not None else None
    accounting = RecurrenceAccountingNode(n=int(root_n), m=max(1,v), operation_kind="exact_log_relation_upcc_full_string_unaccounted", canonical=True, cost_certified=False, local_log2_cost_bound=0.0, children=(), terminal_certified=True, reason="rev198 exact full-ground UPCC closure; global recurrence charge remains uncertified")
    return replace(base, status="exact_empty_log_relation_upcc_full_string" if coset is None else "exact_log_relation_upcc_full_string_coset", coset=coset, operation_kind="log_relation_upcc_full_string", exact=True, local_cost_certified=False, local_log2_cost_bound=float(upcc.local_log2_cost_bound), terminal_certified=True, children=(), accounting=accounting, permutation_candidates_checked=base.permutation_candidates_checked + int(upcc.partition_pair_count), reason="rev184 homogeneous log relation is a rev197/rev198 certified full-ground UPCC; exact SI set closed, recurrence accounting remains open")

signed_johnson_log_certificate_design_descent_si = signed_johnson_log_certificate_design_descent_si_v2
__all__=["_exact_upcc_from_relation","signed_johnson_log_certificate_design_descent_si_v2","signed_johnson_log_certificate_design_descent_si"]
