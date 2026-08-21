from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import design_full_string_child_preflight_v1 as preflight
import design_original_root_pipeline_resource_v1 as root_ledger
import design_primitive_johnson_complete_cover_preflight_v1 as rev254
import design_tuple_full_string_union_si_v1 as caller
import u2_candidate_coset_string_iso_v2 as u2


class _Group:
    def __init__(self, degree=6, order=12, generators=2):
        self.degree = degree
        self.order = order
        self.original_generators = tuple(object() for _ in range(generators))


class _Branch:
    def __init__(self, group):
        self.coset = SimpleNamespace(subgroup=group, representative=tuple(range(group.degree)))


def _classification(status="primitive_non_giant", canonical=True):
    return SimpleNamespace(status=status, canonical=canonical, block_system=None, reason="classified")


def _johnson_envelope(*, work=40, root=10, degree=6, order=12, generators=2):
    return SimpleNamespace(
        resource_admitted=True,
        root_lift_certified=True,
        original_root_degree=root,
        original_degree=degree,
        image_degree=degree,
        parent_order_upper_bound=order,
        image_order_upper_bound=order,
        generator_upper_bound=generators,
        johnson_parameter_candidates=((4, 2),),
        partition_state_upper_bound=64,
        partition_action_upper_bound=128,
        original_root_lift_work_upper_bound=9,
        work_upper_bound=work,
        reason="reserved",
    )


class Rev255PrimitiveJohnsonCallerIntegrationTests(TestCase):
    def test_preflight_selects_primitive_johnson_only_after_cheaper_terminals_fail(self):
        branches = (_Branch(_Group()),)
        rejected_state = SimpleNamespace(
            admitted=False,
            work_upper_bound=1000,
            state_image_upper_bound=1000,
        )
        with patch.object(preflight, "_group_orbits", return_value=((0, 1, 2, 3, 4, 5),)), \
             patch.object(preflight, "state_orbit_candidate_envelope", return_value=rejected_state), \
             patch.object(preflight, "classify_s1_structure", return_value=_classification()), \
             patch.object(rev254, "classify_s1_structure", return_value=_classification()), \
             patch.object(rev254, "design_nested_primitive_johnson_resource_envelope", return_value=_johnson_envelope()):
            plan = preflight.design_full_string_child_preflight(
                branches,
                original_root_degree=10,
                original_degree=6,
                group_order_poly_power=1,
                max_group_order=8,
                max_work=100,
                target_values=(0, 1, 0, 1, 0, 1),
            )
        self.assertTrue(plan.admitted)
        self.assertEqual(plan.terminal_kinds, ("primitive_johnson",))
        self.assertEqual(plan.primitive_johnson_work_upper_bounds, (40,))
        self.assertIsNotNone(plan.primitive_johnson_preflight)
        self.assertTrue(plan.primitive_johnson_preflight.admitted)
        self.assertEqual(plan.primitive_johnson_preflight.candidate_branch_indices, (0,))
        self.assertEqual(plan.permutation_scan_upper_bounds, (128,))

    def test_preflight_fails_closed_when_complete_primitive_subcover_cannot_be_reserved(self):
        branches = (_Branch(_Group()),)
        rejected_state = SimpleNamespace(
            admitted=False,
            work_upper_bound=1000,
            state_image_upper_bound=1000,
        )
        rejected_envelope = _johnson_envelope(work=101)
        rejected_envelope.resource_admitted = False
        with patch.object(preflight, "_group_orbits", return_value=((0, 1, 2, 3, 4, 5),)), \
             patch.object(preflight, "state_orbit_candidate_envelope", return_value=rejected_state), \
             patch.object(preflight, "classify_s1_structure", return_value=_classification()), \
             patch.object(rev254, "classify_s1_structure", return_value=_classification()), \
             patch.object(rev254, "design_nested_primitive_johnson_resource_envelope", return_value=rejected_envelope):
            plan = preflight.design_full_string_child_preflight(
                branches,
                original_root_degree=10,
                original_degree=6,
                group_order_poly_power=1,
                max_group_order=8,
                max_work=100,
                target_values=(0, 1, 0, 1, 0, 1),
            )
        self.assertFalse(plan.admitted)
        self.assertEqual(plan.terminal_kinds, ("unresolved_exact_terminal",))
        self.assertEqual(plan.status, "design_full_string_exact_terminal_cover_unavailable")

    def test_u2_passes_exact_rev254_bounds_to_rev246_without_erasing_unresolved_proof(self):
        group = _Group()
        candidate = SimpleNamespace(subgroup=group, representative=tuple(range(group.degree)))
        reservation = SimpleNamespace(
            selected=True,
            reserved_work_upper_bound=77,
            parent_order_upper_bound=13,
            image_order_upper_bound=13,
            generator_upper_bound=3,
        )
        unresolved = SimpleNamespace(exact=False, status="undetermined_profile")
        small = SimpleNamespace(exact=False)
        with patch.object(u2, "exact_small_order_candidate_string_isomorphism", return_value=small), \
             patch.object(u2, "_group_orbits", return_value=((0, 1, 2, 3, 4, 5),)), \
             patch.object(u2, "classify_s1_structure", return_value=_classification()), \
             patch.object(u2, "resource_bounded_primitive_johnson_string_isomorphism", return_value=unresolved) as bounded:
            result = u2.candidate_coset_string_isomorphism_u2(
                candidate,
                (0, 1, 0, 1, 0, 1),
                (0, 1, 0, 1, 0, 1),
                root_n=10,
                max_explicit_degree=6,
                max_group_order=8,
                primitive_johnson_reservation=reservation,
            )
        self.assertIs(result, unresolved)
        kwargs = bounded.call_args.kwargs
        self.assertEqual(kwargs["parent_order_upper_bound"], 13)
        self.assertEqual(kwargs["image_order_upper_bound"], 13)
        self.assertEqual(kwargs["generator_upper_bound"], 3)
        self.assertEqual(kwargs["max_primitive_johnson_work"], 77)

    def test_full_string_caller_completes_rev254_execution_ledger_before_union(self):
        reservation = SimpleNamespace(branch_index=0, selected=True)
        primitive_plan = SimpleNamespace(
            branch_reservations=(reservation,),
            selected_branch_count=1,
            execution_charge_complete=False,
        )
        child_plan = preflight.DesignFullStringChildPreflight(
            status="certified_design_full_string_exact_terminal_cover_preflight",
            original_root_degree=10,
            original_degree=6,
            branch_count=1,
            subgroup_orders=(12,),
            small_order_gate=8,
            work_per_branch_upper_bounds=(77,),
            work_upper_bound=77,
            max_work=100,
            root_lift_certified=True,
            terminal_path_certified=True,
            admitted=True,
            executed_branch_count=0,
            permutation_candidates_checked=0,
            complete=False,
            reason="test reservation",
            terminal_kinds=("primitive_johnson",),
            permutation_scan_upper_bounds=(128,),
            state_orbit_work_upper_bounds=(0,),
            state_orbit_image_upper_bounds=(0,),
            imprimitive_work_upper_bounds=(0,),
            primitive_johnson_work_upper_bounds=(77,),
            primitive_johnson_preflight=primitive_plan,
        )
        proof = SimpleNamespace(
            exact=True,
            coset=None,
            production_attempt_admitted=True,
            permutation_candidates_checked=3,
            local_log2_cost_bound=1.0,
        )
        transport = SimpleNamespace(
            exact_empty=False,
            complete=True,
            status="certified_complete_design_tuple_transport_cover",
            branches=(SimpleNamespace(coset=SimpleNamespace(representative=tuple(range(6)))),),
            surviving_branch_count=1,
            local_log2_cost_bound=1.0,
        )
        ambient = SimpleNamespace(degree=6, contains=lambda p: True)
        recorded_partial = SimpleNamespace(
            branch_reservations=(reservation,),
            selected_branch_count=1,
            execution_charge_complete=False,
        )
        recorded_complete = SimpleNamespace(
            branch_reservations=(reservation,),
            selected_branch_count=1,
            execution_charge_complete=True,
        )
        with patch.object(caller, "design_full_string_child_preflight", return_value=child_plan), \
             patch.object(caller, "candidate_coset_string_isomorphism_u2", return_value=proof) as run_child, \
             patch.object(caller, "record_design_primitive_johnson_complete_cover_execution", side_effect=(recorded_partial, recorded_complete)) as record_primitive, \
             patch.object(caller, "record_design_full_string_child_execution", side_effect=lambda plan, children, complete: plan), \
             patch.object(caller, "certify_design_full_string_child_resources", return_value=SimpleNamespace(certified=True, reason="ok")):
            result = caller.solve_design_tuple_transport_full_string(
                ambient,
                transport,
                (0, 1, 0, 1, 0, 1),
                (0, 1, 0, 1, 0, 1),
                root_n=10,
            )
        self.assertTrue(result.exact)
        self.assertEqual(result.status, "exact_empty_design_tuple_full_string_union")
        self.assertEqual(record_primitive.call_count, 2)
        self.assertFalse(record_primitive.call_args_list[0].kwargs["complete"])
        self.assertTrue(record_primitive.call_args_list[1].kwargs["complete"])
        self.assertIs(run_child.call_args.kwargs["primitive_johnson_reservation"], reservation)
        self.assertTrue(result.child_preflight.primitive_johnson_preflight.execution_charge_complete)

    def test_original_root_children_reservation_includes_primitive_johnson_envelope(self):
        twl = SimpleNamespace(
            individualization_runs_per_side_upper_bound=1,
            paired_work_upper_bound=2,
            root_lift_certified=True,
        )
        material = SimpleNamespace(branch_count=2, work_upper_bound=3, root_lift_certified=True)
        transport = SimpleNamespace(work_upper_bound=5, root_lift_certified=True)
        primitive = SimpleNamespace(work_upper_bound=123)
        group = _Group(degree=6, order=12, generators=2)
        with patch.object(root_ledger, "paired_correlated_twl_resource_envelope", return_value=twl), \
             patch.object(root_ledger, "design_branch_materialization_resource_envelope", return_value=material), \
             patch.object(root_ledger, "design_tuple_transport_resource_envelope", return_value=transport), \
             patch.object(root_ledger, "design_nested_primitive_johnson_resource_envelope", return_value=primitive):
            envelope = root_ledger.design_original_root_pipeline_resource_envelope(
                group,
                original_root_degree=10,
                vertex_count=4,
                arity=2,
                target_values=(0, 1, 0, 1, 0, 1),
                group_order_poly_power=1,
                max_group_order=8,
                max_work=10**30,
            )
        children_bound = envelope.phase_work_upper_bounds[3]
        self.assertGreaterEqual(children_bound, 2 * 123)


if __name__ == "__main__":
    import unittest
    unittest.main()
