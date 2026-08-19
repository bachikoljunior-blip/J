from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import ceil, comb, log2

from design_lemma_candidate_si_v1 import DesignLemmaCandidateSI, design_lemma_candidate_string_isomorphism
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from signed_johnson_complement_safe_image_si_v1 import complement_safe_t_relation_signatures
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_log_certificate_design_descent_si_v1 import (
    SignedJohnsonLogCertificateProof,
    signed_johnson_log_certificate_design_descent_si,
)


@dataclass(frozen=True)
class W1RH6LogDesignProof:
    status: str
    coset: object | None
    h5_result: SignedJohnsonLogCertificateProof
    design_result: DesignLemmaCandidateSI | None
    ground_size: int
    subset_size: int
    test_arity: int
    test_count: int
    theorem_parameter_gate: bool
    exact: bool
    local_cost_certified: bool
    local_log2_cost_bound: float
    reason: str


def signed_johnson_log_design_lemma_si_v2(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    alpha: float = 0.9,
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
    max_design_states: int = 200000,
    max_design_wl_vertices: int = 512,
    max_design_wl_rounds: int = 4096,
    max_design_branch_pairs: int = 200000,
) -> W1RH6LogDesignProof:
    """Connect H5 logarithmic relation generation to the exact H6 Design path.

    The rev184/H5 implementation remains authoritative for Johnson recognition,
    logarithmic arity/test-count gates, invariant mismatch, point-split transport,
    and lower-arity Johnson descent. Only its final homogeneous-design failure is
    intercepted. For that case this wrapper deterministically reconstructs the
    exact same complement-safe logarithmic relation, verifies consistency with
    the H5 proof boundary, then invokes the rev190 exact Design-Lemma candidate SI
    composition on the original ambient group and full string.

    Exact H6 output is exposed only when every Design branch is exact. Otherwise
    the result stays unresolved. The explicit local bounds from H5 and Design
    composition are accumulated, but `local_cost_certified` remains false on the
    new Design path until a global quasipolynomial recurrence proof incorporates
    the complete branching charge. Thus this closes an execution/interface gap
    without lowering the theorem-scale complexity criterion.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n

    h5 = signed_johnson_log_certificate_design_descent_si(
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
    if h5.status != "undetermined_log_certificate_design_gate":
        return W1RH6LogDesignProof(
            "delegated_" + h5.status,
            h5.coset,
            h5,
            None,
            h5.ground_size,
            h5.subset_size,
            h5.test_arity,
            h5.test_count,
            h5.theorem_parameter_gate,
            h5.exact,
            h5.local_cost_certified,
            h5.local_log2_cost_bound,
            "H5 resolved or typed this instance before the homogeneous Design-Lemma gate, so H6 preserves that proof result unchanged",
        )

    lift = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=max_recognition_nodes,
    )
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        raise AssertionError("H5 reached its Design gate but recomputed Johnson lift is not exact")
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    arity_cap = max(1, ceil(log2(max(2, root_n))))
    t = min(k - 1, max(2, ceil(log2(max(2, v)))))
    test_count = comb(v, t)
    if (v, k, t, test_count) != (h5.ground_size, h5.subset_size, h5.test_arity, h5.test_count):
        raise AssertionError("recomputed H6 logarithmic relation parameters disagree with the H5 proof boundary")
    if not h5.theorem_parameter_gate or t > arity_cap or test_count > max_test_sets:
        raise AssertionError("H5 Design gate was reached without its logarithmic parameter gate")

    complement = any(bool(g.complement) for g in lift.lifted_generators)
    source_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    target_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)
    source_relation = complement_safe_t_relation_signatures(
        v, k, source_tokens, t, complement_in_image=complement
    )
    target_relation = complement_safe_t_relation_signatures(
        v, k, target_tokens, t, complement_in_image=complement
    )
    if len(source_relation) != test_count or len(target_relation) != test_count:
        raise AssertionError("H6 logarithmic relation size mismatch")
    if Counter(source_relation) != Counter(target_relation):
        raise AssertionError("H5 Design gate was reached despite a relation multiplicity mismatch")

    design = design_lemma_candidate_string_isomorphism(
        group,
        lift.lifted_generators,
        v,
        t,
        source_relation,
        target_relation,
        source,
        target,
        root_n=root_n,
        alpha=alpha,
        max_states=max_design_states,
        max_wl_vertices=max_design_wl_vertices,
        max_wl_rounds=max_design_wl_rounds,
        max_branch_pairs=max_design_branch_pairs,
        max_partition_states=max_partition_states,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=candidate_group_order_poly_power,
        max_group_order=max_candidate_group_order,
        max_depth=max_depth,
    )
    explicit_bound = (
        h5.local_log2_cost_bound
        + design.local_log2_cost_bound
        + 8.0 * log2(max(2, root_n))
        + 32.0
    )
    if not design.exact:
        return W1RH6LogDesignProof(
            "undetermined_w1r_h6_design_candidate",
            None,
            h5,
            design,
            v,
            k,
            t,
            test_count,
            bool(h5.theorem_parameter_gate and design.theorem_hypotheses_certified),
            False,
            False,
            explicit_bound,
            "H5 homogeneous logarithmic relation reached the exact Design-Lemma machinery, but at least one theorem/resource/full-string branch remains unresolved",
        )

    coset = None if design.full_string_result is None else design.full_string_result.coset
    return W1RH6LogDesignProof(
        "exact_w1r_h6_design_full_string",
        coset,
        h5,
        design,
        v,
        k,
        t,
        test_count,
        bool(h5.theorem_parameter_gate and design.theorem_hypotheses_certified),
        True,
        False,
        explicit_bound,
        "the H5 homogeneous logarithmic relation was connected to a complete exact Design-Lemma branch/full-string solution; global quasipolynomial recurrence certification remains intentionally withheld",
    )
