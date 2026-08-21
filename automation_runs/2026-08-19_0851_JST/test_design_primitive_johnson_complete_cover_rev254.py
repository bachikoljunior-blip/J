from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import design_primitive_johnson_complete_cover_preflight_v1 as rev254


class _Group:
    def __init__(self, degree: int, order: int, generator_count: int = 2):
        self.degree = degree
        self.order = order
        self.original_generators = tuple(object() for _ in range(generator_count))


class _Branch:
    def __init__(self, group: _Group):
        self.coset = SimpleNamespace(subgroup=group)


def _classification(status: str = "primitive_non_giant", canonical: bool = True):
    return SimpleNamespace(status=status, canonical=canonical)


def _envelope(
    *,
    work: int = 40,
    root_work: int = 9,
    admitted: bool = True,
    root: int = 10,
    degree: int = 6,
    order: int = 12,
    generators: int = 2,
):
    return SimpleNamespace(
        resource_admitted=admitted,
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
        original_root_lift_work_upper_bound=root_work,
        work_upper_bound=work,
        reason="reserved" if admitted else "rejected",
    )


def _result(envelope, *, charged: int):
    return SimpleNamespace(
        production_attempt_admitted=True,
        classification_status="primitive_non_giant",
        resource_envelope=envelope,
        charged_work_upper_bound=charged,
    )


class Rev254PrimitiveJohnsonCompleteCoverTests(TestCase):
    def setUp(self):
        self.branches = (
            _Branch(_Group(6, 12, 2)),
            _Branch(_Group(6, 12, 2)),
            _Branch(_Group(6, 12, 2)),
        )

    def test_selects_only_caller_unresolved_indices(self):
        with patch.object(rev254, "classify_s1_structure", return_value=_classification()) as classify, patch.object(
            rev254,
            "design_nested_primitive_johnson_resource_envelope",
            return_value=_envelope(),
        ) as reserve:
            plan = rev254.design_primitive_johnson_complete_cover_preflight(
                self.branches,
                original_root_degree=10,
                original_degree=6,
                candidate_branch_indices=(2, 0),
                max_work=100,
            )
        self.assertTrue(plan.admitted)
        self.assertEqual(plan.candidate_branch_indices, (0, 2))
        self.assertEqual(tuple(r.branch_index for r in plan.branch_reservations), (0, 2))
        self.assertEqual(plan.selected_branch_count, 2)
        self.assertEqual(plan.work_upper_bound, 80)
        self.assertEqual(plan.root_lift_work_upper_bound, 18)
        self.assertEqual(classify.call_count, 2)
        self.assertEqual(reserve.call_count, 2)

    def test_nonprimitive_selected_branch_rejects_entire_subcover_before_execution(self):
        with patch.object(
            rev254,
            "classify_s1_structure",
            return_value=_classification("canonical_imprimitive_block_system"),
        ), patch.object(rev254, "design_nested_primitive_johnson_resource_envelope") as reserve:
            plan = rev254.design_primitive_johnson_complete_cover_preflight(
                self.branches,
                original_root_degree=10,
                original_degree=6,
                candidate_branch_indices=(1,),
                max_work=100,
            )
        self.assertFalse(plan.admitted)
        self.assertFalse(plan.complete_selection)
        self.assertEqual(plan.status, "design_primitive_johnson_complete_cover_path_unavailable")
        reserve.assert_not_called()

    def test_resource_rejection_is_fail_closed(self):
        with patch.object(rev254, "classify_s1_structure", return_value=_classification()), patch.object(
            rev254,
            "design_nested_primitive_johnson_resource_envelope",
            return_value=_envelope(work=101, admitted=False),
        ):
            plan = rev254.design_primitive_johnson_complete_cover_preflight(
                self.branches,
                original_root_degree=10,
                original_degree=6,
                candidate_branch_indices=(0,),
                max_work=100,
            )
        self.assertFalse(plan.admitted)
        self.assertEqual(plan.status, "design_primitive_johnson_complete_cover_resource_unavailable")

    def test_aggregate_cover_cap_is_checked_before_first_execution(self):
        with patch.object(rev254, "classify_s1_structure", return_value=_classification()), patch.object(
            rev254,
            "design_nested_primitive_johnson_resource_envelope",
            side_effect=(_envelope(work=60), _envelope(work=60)),
        ):
            plan = rev254.design_primitive_johnson_complete_cover_preflight(
                self.branches,
                original_root_degree=10,
                original_degree=6,
                candidate_branch_indices=(0, 1),
                max_work=100,
            )
        self.assertFalse(plan.admitted)
        self.assertEqual(plan.work_upper_bound, 101)
        self.assertEqual(plan.status, "design_primitive_johnson_complete_cover_work_cap_exceeded")

    def test_original_root_lift_failure_does_not_classify_or_reserve(self):
        with patch.object(rev254, "classify_s1_structure") as classify, patch.object(
            rev254,
            "design_nested_primitive_johnson_resource_envelope",
        ) as reserve:
            plan = rev254.design_primitive_johnson_complete_cover_preflight(
                self.branches,
                original_root_degree=5,
                original_degree=6,
                candidate_branch_indices=(0,),
                max_work=100,
            )
        self.assertFalse(plan.admitted)
        self.assertFalse(plan.root_lift_certified)
        self.assertEqual(
            plan.status,
            "design_primitive_johnson_complete_cover_original_root_lift_unavailable",
        )
        classify.assert_not_called()
        reserve.assert_not_called()

    def test_empty_selected_subcover_is_exact_noop(self):
        plan = rev254.design_primitive_johnson_complete_cover_preflight(
            self.branches,
            original_root_degree=10,
            original_degree=6,
            candidate_branch_indices=(),
            max_work=100,
        )
        self.assertTrue(plan.admitted)
        self.assertTrue(plan.complete_selection)
        self.assertEqual(plan.work_upper_bound, 0)
        self.assertEqual(plan.selected_branch_count, 0)

    def test_complete_execution_binds_rev246_charges_to_reserved_cover(self):
        envelopes = (_envelope(work=40), _envelope(work=45))
        with patch.object(rev254, "classify_s1_structure", return_value=_classification()), patch.object(
            rev254,
            "design_nested_primitive_johnson_resource_envelope",
            side_effect=envelopes,
        ):
            plan = rev254.design_primitive_johnson_complete_cover_preflight(
                self.branches,
                original_root_degree=10,
                original_degree=6,
                candidate_branch_indices=(0, 2),
                max_work=100,
            )
        recorded = rev254.record_design_primitive_johnson_complete_cover_execution(
            plan,
            (_result(envelopes[0], charged=35), _result(envelopes[1], charged=40)),
            complete=True,
        )
        self.assertTrue(recorded.execution_charge_complete)
        self.assertEqual(recorded.executed_branch_count, 2)
        self.assertEqual(recorded.charged_work_upper_bound, 75)
        self.assertLessEqual(recorded.charged_work_upper_bound, recorded.work_upper_bound)

    def test_forged_larger_rev246_envelope_is_rejected(self):
        reserved = _envelope(work=40, order=12)
        with patch.object(rev254, "classify_s1_structure", return_value=_classification()), patch.object(
            rev254,
            "design_nested_primitive_johnson_resource_envelope",
            return_value=reserved,
        ):
            plan = rev254.design_primitive_johnson_complete_cover_preflight(
                self.branches,
                original_root_degree=10,
                original_degree=6,
                candidate_branch_indices=(0,),
                max_work=100,
            )
        forged = _envelope(work=40, order=13)
        with self.assertRaisesRegex(ValueError, "parent_order_upper_bound"):
            rev254.record_design_primitive_johnson_complete_cover_execution(
                plan,
                (_result(forged, charged=35),),
                complete=True,
            )

    def test_complete_record_cannot_omit_selected_branch(self):
        with patch.object(rev254, "classify_s1_structure", return_value=_classification()), patch.object(
            rev254,
            "design_nested_primitive_johnson_resource_envelope",
            side_effect=(_envelope(work=30), _envelope(work=30)),
        ):
            plan = rev254.design_primitive_johnson_complete_cover_preflight(
                self.branches,
                original_root_degree=10,
                original_degree=6,
                candidate_branch_indices=(0, 1),
                max_work=100,
            )
        with self.assertRaisesRegex(ValueError, "omitted"):
            rev254.record_design_primitive_johnson_complete_cover_execution(
                plan,
                (_result(plan.branch_reservations[0].resource_envelope, charged=20),),
                complete=True,
            )

    def test_duplicate_candidate_indices_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            rev254.design_primitive_johnson_complete_cover_preflight(
                self.branches,
                original_root_degree=10,
                original_degree=6,
                candidate_branch_indices=(1, 1),
                max_work=100,
            )


if __name__ == "__main__":
    import unittest

    unittest.main()
