from design_full_string_child_resource_proof_v1 import certify_design_full_string_child_resources
from proof_carrying_si_v1 import explicit_small_coset_intersection_proof
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _child(n=4, root=16):
    group = schreier_stabilizer_chain((identity(n),))
    coset = RightCoset(group, identity(n))
    return explicit_small_coset_intersection_proof(coset, coset, root_n=root)


def test_complete_children_are_each_accounted_once():
    children = (_child(), _child())
    proof = certify_design_full_string_child_resources(
        children, expected_branch_count=2, original_root_degree=16,
    )
    assert proof.certified and proof.accounted_branch_count == 2
    assert len(proof.child_log2_work_bounds) == 2
    assert proof.combined_log2_work_bound > max(proof.child_log2_work_bounds)


def test_missing_child_is_fail_closed():
    proof = certify_design_full_string_child_resources(
        (_child(),), expected_branch_count=2, original_root_degree=16,
    )
    assert not proof.certified
    assert proof.status == "incomplete_design_full_string_child_execution"
