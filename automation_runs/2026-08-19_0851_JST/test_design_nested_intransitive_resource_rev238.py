from design_nested_intransitive_resource_v1 import (
    design_nested_intransitive_resource_envelope,
)


def test_strict_smaller_tree_is_finite_but_does_not_claim_path_admission():
    proof = design_nested_intransitive_resource_envelope(
        original_root_degree=8,
        original_degree=8,
        image_degree=5,
        image_order_upper_bound=60,
        generator_upper_bound=4,
        small_order_gate=6,
        max_work=10**100,
    )
    assert proof.status == "certified_conditional_design_nested_intransitive_resource_envelope"
    assert proof.strict_degree_progress_certified
    assert proof.recursion_node_upper_bound == 1 + 5 * (1 + 4 * 1)
    assert proof.terminal_leaf_upper_bound == 5 * 4
    assert proof.permutation_scan_upper_bound == 5 * 4 * 12
    assert proof.work_upper_bound <= proof.max_work
    assert not proof.conditional_path_certified
    assert not proof.admitted


def test_order_is_reduced_by_child_symmetric_group_bound():
    # 24 is above the gate at degree four, but every strict child has degree at
    # most three and image order at most 3! = 6, so recursion stops immediately.
    proof = design_nested_intransitive_resource_envelope(
        original_root_degree=7,
        original_degree=7,
        image_degree=4,
        image_order_upper_bound=24,
        generator_upper_bound=3,
        small_order_gate=6,
        max_work=10**80,
    )
    assert proof.recursion_node_upper_bound == 5
    assert proof.terminal_leaf_upper_bound == 4
    assert proof.permutation_scan_upper_bound == 48


def test_work_saturates_at_caller_cap_plus_one():
    proof = design_nested_intransitive_resource_envelope(
        original_root_degree=9,
        original_degree=9,
        image_degree=6,
        image_order_upper_bound=720,
        generator_upper_bound=6,
        small_order_gate=6,
        max_work=97,
    )
    assert proof.status == "design_nested_intransitive_work_cap_exceeded"
    assert proof.work_upper_bound == 98
    assert not proof.admitted


def test_invalid_permutation_order_is_rejected():
    try:
        design_nested_intransitive_resource_envelope(
            original_root_degree=5,
            original_degree=5,
            image_degree=4,
            image_order_upper_bound=25,
            generator_upper_bound=2,
            small_order_gate=4,
            max_work=1000,
        )
    except ValueError as exc:
        assert "symmetric group order" in str(exc)
    else:
        raise AssertionError("invalid image order was accepted")
