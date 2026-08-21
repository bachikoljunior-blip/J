from itertools import combinations
from unittest.mock import patch

from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from resource_bounded_primitive_johnson_candidate_si_v1 import (
    resource_bounded_primitive_johnson_string_isomorphism,
)


def _cycle(v):
    return tuple((i + 1) % v for i in range(v))


def _swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def _induced_ground_group(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(index[tuple(sorted(sigma[x] for x in subset))] for subset in subsets)

    generators = tuple(induce(g) for g in (_swap01(v), _cycle(v)))
    return schreier_stabilizer_chain(generators), generators, subsets


def _relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def _membership_count_colors(subsets, marked):
    marked = set(marked)
    return tuple(sum(x in marked for x in subset) for subset in subsets)


def _maps_string(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def _j92_instance():
    group, generators, subsets = _induced_ground_group(9, 2)
    source = _membership_count_colors(subsets, range(4))
    target = _relabel_target(source, generators[1])
    return group, generators[1], source, target


def test_rev246_executes_profile_terminal_under_the_exact_rev243_reservation():
    group, witness, source, target = _j92_instance()
    got = resource_bounded_primitive_johnson_string_isomorphism(
        group,
        source,
        target,
        root_n=64,
        max_partition_states=1024,
        max_primitive_johnson_work=10**400,
    )

    assert got.structural_path_certified
    assert got.johnson_path_certified
    assert got.execution_charge_complete
    assert got.production_attempt_admitted
    assert got.resource_envelope is not None
    assert got.resource_envelope.resource_admitted
    assert got.johnson_parameter_executed == (9, 2)
    assert got.charged_work_upper_bound == got.resource_envelope.work_upper_bound
    assert got.partition_states_executed <= got.resource_envelope.partition_state_upper_bound
    assert got.partition_actions_executed <= got.resource_envelope.partition_action_upper_bound
    assert got.exact and got.coset is not None, got
    assert got.coset.contains(witness)
    assert _maps_string(source, target, got.coset.representative)
    assert validate_quasipoly_recurrence_tree_v4(got.accounting).certified


def test_rev246_rejects_work_cap_before_johnson_semantic_execution():
    group, _witness, source, target = _j92_instance()
    with patch(
        "resource_bounded_primitive_johnson_candidate_si_v1.signed_johnson_ground_profile_partition_si",
        side_effect=AssertionError("semantic solver must not run before resource admission"),
    ):
        got = resource_bounded_primitive_johnson_string_isomorphism(
            group,
            source,
            target,
            root_n=64,
            max_partition_states=1024,
            max_primitive_johnson_work=17,
        )
    assert not got.exact
    assert got.resource_envelope is not None
    assert not got.resource_envelope.resource_admitted
    assert got.status == "design_nested_primitive_johnson_work_cap_exceeded"
    assert not got.execution_charge_complete
    assert not got.production_attempt_admitted


def test_rev246_rejects_understated_prechild_order_bound_before_execution():
    group, _witness, source, target = _j92_instance()
    got = resource_bounded_primitive_johnson_string_isomorphism(
        group,
        source,
        target,
        root_n=64,
        image_order_upper_bound=group.order - 1,
        max_primitive_johnson_work=10**400,
    )
    assert not got.exact
    assert got.status == "primitive_johnson_prechild_bound_below_actual_execution"
    assert got.structural_path_certified
    assert got.resource_envelope is None
    assert not got.execution_charge_complete


def test_rev246_partition_cap_stays_fail_closed_but_is_execution_linked():
    group, _witness, source, target = _j92_instance()
    got = resource_bounded_primitive_johnson_string_isomorphism(
        group,
        source,
        target,
        root_n=64,
        max_partition_states=8,
        max_primitive_johnson_work=10**400,
    )
    assert not got.exact
    assert "partition_orbit_limit" in got.status
    assert got.structural_path_certified
    assert got.johnson_path_certified
    assert got.execution_charge_complete
    assert got.production_attempt_admitted
    assert got.partition_states_executed <= 8


def test_rev246_non_johnson_primitive_degree_never_enters_semantic_solver():
    group = schreier_stabilizer_chain((_cycle(11),))
    source = tuple(range(11))
    with patch(
        "resource_bounded_primitive_johnson_candidate_si_v1.signed_johnson_ground_profile_partition_si",
        side_effect=AssertionError("non-Johnson degree must fail in the resource preflight"),
    ):
        got = resource_bounded_primitive_johnson_string_isomorphism(
            group,
            source,
            source,
            root_n=64,
            max_primitive_johnson_work=10**200,
        )
    assert got.structural_path_certified
    assert got.resource_envelope is not None
    assert got.status == "design_nested_primitive_johnson_no_parameter_candidate"
    assert not got.resource_envelope.resource_admitted
    assert not got.johnson_path_certified
    assert not got.execution_charge_complete
