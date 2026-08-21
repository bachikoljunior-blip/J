from types import SimpleNamespace

from coset_stabilizer_primitives import RightCoset
from design_full_string_child_preflight_v1 import design_full_string_child_preflight
from design_original_root_pipeline_resource_v1 import design_original_root_pipeline_resource_envelope
from permutation_group_schreier import identity
from test_imprimitive_quotient_kernel_resource_rev244 import large_unique_imprimitive_group
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


def _branch(group):
    return SimpleNamespace(coset=RightCoset(group, identity(group.degree)))


def test_shared_pipeline_reserves_structured_imprimitive_child_before_twl():
    group = large_unique_imprimitive_group()
    got = design_original_root_pipeline_resource_envelope(
        group,
        original_root_degree=64,
        vertex_count=4,
        arity=2,
        target_values=(0,) * group.degree,
        group_order_poly_power=2,
        max_group_order=16,
        max_work=10**100,
    )
    assert got.admitted
    assert got.phase_work_upper_bounds[3] >= (2 ** 26) * (group.degree ** 12) * (group.order ** 3)


def test_complete_cover_selects_rev244_imprimitive_terminal():
    group = large_unique_imprimitive_group()
    got = design_full_string_child_preflight(
        (_branch(group),),
        original_root_degree=64,
        original_degree=group.degree,
        group_order_poly_power=2,
        max_group_order=16,
        max_work=10**40,
        target_values=(0,) * group.degree,
    )
    assert got.admitted
    assert got.terminal_kinds == ("imprimitive_quotient_kernel",)
    assert got.imprimitive_work_upper_bounds[0] == got.work_per_branch_upper_bounds[0]


def test_design_u2_executes_reserved_imprimitive_operator_exactly():
    group = large_unique_imprimitive_group()
    got = candidate_coset_string_isomorphism_u2(
        _branch(group).coset,
        (0,) * group.degree,
        (0,) * group.degree,
        root_n=64,
        max_group_order=16,
        max_state_orbit_work=0,
        max_imprimitive_quotient_kernel_work=10**40,
    )
    assert got.exact and got.coset is not None
    assert got.coset.subgroup.order == group.order
    assert got.operation_kind == "imprimitive_small_quotient"
