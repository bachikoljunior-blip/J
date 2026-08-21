from math import comb

from design_nested_primitive_johnson_resource_v1 import (
    design_nested_primitive_johnson_resource_envelope,
)


def _proof(**overrides):
    kwargs = dict(
        original_root_degree=12,
        original_degree=10,
        image_degree=10,
        parent_order_upper_bound=720,
        image_order_upper_bound=120,
        generator_upper_bound=4,
        max_recognition_nodes=12,
        max_robust_orbital_degree=128,
        partition_state_poly_power=2,
        max_partition_states=64,
        max_work=10**200,
    )
    kwargs.update(overrides)
    return design_nested_primitive_johnson_resource_envelope(**kwargs)


def test_johnson_parameter_family_is_complete_before_unknown_subgroup():
    proof = _proof()
    assert proof.status == "certified_design_nested_primitive_johnson_resource_preflight"
    assert proof.johnson_parameter_candidates == ((5, 2),)
    assert proof.max_ground_size == 5
    assert proof.strict_ground_progress_certified
    assert proof.johnson_parameter_cover_certified
    assert proof.recognition_comparison_upper_bound == 3 * comb(10, 2)
    assert proof.partition_state_upper_bound == 64
    assert proof.partition_action_upper_bound == 256
    assert proof.work_upper_bound <= proof.max_work
    assert proof.resource_admitted
    assert proof.admitted
    assert not proof.exact_path_certified


def test_signed_complement_parameter_gets_two_v_factorial_coverage():
    proof = _proof(
        original_root_degree=24,
        original_degree=20,
        image_degree=20,
        parent_order_upper_bound=10**6,
        image_order_upper_bound=1440,
        generator_upper_bound=5,
        max_partition_states=25,
        max_work=10**240,
    )
    assert proof.johnson_parameter_candidates == ((6, 3),)
    assert proof.max_ground_size == 6
    assert proof.max_subset_size == 3
    assert proof.johnson_action_order_certified
    assert proof.resource_admitted


def test_robust_fallback_is_not_reserved_above_explicit_degree_cap():
    proof = _proof(
        original_root_degree=18,
        original_degree=15,
        image_degree=15,
        parent_order_upper_bound=10**6,
        image_order_upper_bound=720,
        max_robust_orbital_degree=10,
        max_work=10**220,
    )
    assert proof.johnson_parameter_candidates == ((6, 2),)
    assert proof.recognition_comparison_upper_bound == comb(15, 2)
    assert proof.resource_admitted


def test_work_saturates_at_caller_cap_plus_one_before_recognition():
    proof = _proof(max_work=97)
    assert proof.status == "design_nested_primitive_johnson_work_cap_exceeded"
    assert proof.work_upper_bound == 98
    assert not proof.resource_admitted


def test_non_johnson_degree_fails_closed_without_claiming_a_path():
    proof = _proof(
        original_root_degree=8,
        original_degree=7,
        image_degree=7,
        parent_order_upper_bound=5040,
        image_order_upper_bound=5040,
        max_work=10**80,
    )
    assert proof.status == "design_nested_primitive_johnson_no_parameter_candidate"
    assert proof.johnson_parameter_candidates == ()
    assert proof.recognition_comparison_upper_bound == 0
    assert proof.johnson_parameter_cover_certified
    assert not proof.strict_ground_progress_certified
    assert not proof.resource_admitted


def test_root_lift_and_order_guards_fail_closed():
    proof = _proof(
        original_root_degree=9,
        original_degree=10,
        max_work=10**200,
    )
    assert proof.status == "design_nested_primitive_johnson_original_root_lift_unavailable"
    assert not proof.resource_admitted

    too_large_for_johnson = _proof(image_order_upper_bound=121)
    assert too_large_for_johnson.status == (
        "design_nested_primitive_johnson_action_order_exceeded"
    )
    assert not too_large_for_johnson.johnson_action_order_certified
    assert not too_large_for_johnson.resource_admitted

    try:
        _proof(image_order_upper_bound=721)
    except ValueError as exc:
        assert "image order upper bound" in str(exc)
    else:
        raise AssertionError("image order above its parent was accepted")
