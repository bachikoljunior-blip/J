from __future__ import annotations

import unittest

from crx1_image_si_resource_admission_v1 import (
    CRX1ImageSIExecution,
    CRX1ImageSIRequest,
    crx1_image_si_resource_admission,
    johnson_relation_image_resource_request,
    record_crx1_image_si_execution,
    recursive_coset_intersection_node_upper_bound,
)


def request(
    *,
    degree: int = 4,
    left: int = 6,
    right: int = 24,
    setup: int = 10,
    per_node: int = 5,
    strict: bool = True,
    restricting: bool = True,
    whole: bool = False,
    left_certified: bool = True,
    right_certified: bool = True,
) -> CRX1ImageSIRequest:
    return CRX1ImageSIRequest(
        degree,
        left,
        right,
        setup,
        per_node,
        strict,
        restricting,
        whole,
        left_certified,
        right_certified,
    )


def admit(*items: CRX1ImageSIRequest, **overrides):
    parameters = dict(
        root_degree=10,
        parent_degree=8,
        image_si_poly_power=4,
        max_nodes_per_intersection=1000,
        max_total_nodes=2000,
        max_work=10000,
    )
    parameters.update(overrides)
    return crx1_image_si_resource_admission(items, **parameters)


class CRX1ImageSIResourceAdmissionTests(unittest.TestCase):
    def test_closed_form_node_bound(self):
        self.assertEqual(
            recursive_coset_intersection_node_upper_bound(3, 2, 10),
            48,
        )
        self.assertEqual(
            recursive_coset_intersection_node_upper_bound(3, 2, 10, stop=40),
            40,
        )

    def test_admits_complete_strict_restricting_cover(self):
        certificate = admit(request(), request(left=2, right=12, setup=7, per_node=3))
        self.assertTrue(certificate.admitted)
        self.assertEqual(certificate.status, "certified_crx1_image_si_resource_admission")
        self.assertEqual(certificate.node_upper_bounds, (175, 75))
        self.assertEqual(certificate.total_node_upper_bound, 250)
        self.assertEqual(certificate.work_upper_bounds, (885, 232))
        self.assertEqual(certificate.total_work_upper_bound, 1117)
        self.assertTrue(certificate.exact_intersection_path_certified)
        self.assertFalse(certificate.complete)

    def test_uncertified_order_fails_closed(self):
        certificate = admit(request(left_certified=False))
        self.assertFalse(certificate.admitted)
        self.assertFalse(certificate.orders_certified)
        self.assertEqual(certificate.status, "crx1_image_si_order_certificate_unavailable")
        self.assertEqual(certificate.executed_request_count, 0)

    def test_nonrestricting_same_domain_fails_closed(self):
        certificate = admit(
            request(degree=8, strict=False, restricting=False),
        )
        self.assertFalse(certificate.admitted)
        self.assertEqual(certificate.status, "crx1_image_si_nonrestricting_or_nonshrinking")

    def test_whole_candidate_terminal_allows_same_domain(self):
        certificate = admit(
            request(degree=8, left=1, right=1, strict=False, restricting=False, whole=True),
            max_nodes_per_intersection=1000,
        )
        self.assertTrue(certificate.admitted)
        self.assertTrue(certificate.progress_certified)

    def test_contradictory_strict_progress_is_rejected_as_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "contradicts"):
            admit(request(degree=8, strict=True))

    def test_per_intersection_bound_exceeds_polynomial_gate(self):
        certificate = admit(
            request(degree=8, left=1000, right=1000, setup=1, per_node=1),
            root_degree=10,
            parent_degree=9,
            image_si_poly_power=3,
            max_nodes_per_intersection=200000,
            max_total_nodes=200000,
            max_work=200000,
        )
        self.assertFalse(certificate.admitted)
        self.assertEqual(certificate.polynomial_node_gate, 1000)
        self.assertEqual(certificate.status, "crx1_image_si_per_intersection_node_bound_exceeded")

    def test_complete_cover_node_budget_is_reserved_before_execution(self):
        certificate = admit(
            request(),
            request(),
            max_total_nodes=300,
        )
        self.assertFalse(certificate.admitted)
        self.assertEqual(certificate.total_node_upper_bound, 301)
        self.assertEqual(certificate.status, "crx1_image_si_cover_node_bound_exceeded")
        self.assertEqual(certificate.search_nodes_used, 0)

    def test_work_budget_uses_cap_plus_one_saturation(self):
        certificate = admit(
            request(left=10**100, right=10**100, setup=10**100, per_node=10**100),
            max_nodes_per_intersection=1000,
            max_total_nodes=1000,
            max_work=500,
        )
        self.assertFalse(certificate.admitted)
        self.assertEqual(certificate.node_upper_bounds, (1001,))
        self.assertEqual(certificate.work_upper_bounds, (501,))
        self.assertEqual(certificate.total_work_upper_bound, 501)

    def test_work_bound_is_not_truncated_by_a_smaller_node_sentinel(self):
        certificate = admit(
            request(degree=8, left=10**30, right=10**30, setup=1, per_node=1),
            parent_degree=9,
            max_nodes_per_intersection=1000,
            max_total_nodes=1000,
            max_work=100000,
        )
        self.assertFalse(certificate.admitted)
        self.assertEqual(certificate.node_upper_bounds, (1001,))
        self.assertEqual(certificate.work_upper_bounds, (100001,))

    def test_proof_flags_must_be_real_booleans(self):
        malformed = request()
        malformed = CRX1ImageSIRequest(
            malformed.image_degree,
            malformed.left_coset_order,
            malformed.right_coset_order,
            malformed.setup_work_upper_bound,
            malformed.per_node_work_upper_bound,
            "yes",
            True,
        )
        with self.assertRaisesRegex(ValueError, "must be a boolean"):
            admit(malformed)

    def test_johnson_helper_matches_current_charge_identity(self):
        built = johnson_relation_image_resource_request(
            parent_degree=10,
            auxiliary_degree=5,
            subset_size=2,
            relation_arity=1,
            image_degree=5,
            image_group_order=6,
            value_coset_order=24,
            strict_image_progress_certified=True,
            restricting_preimage_certified=True,
        )
        self.assertEqual(built.setup_work_upper_bound, 400)
        self.assertEqual(built.per_node_work_upper_bound, 20**6)
        certificate = admit(
            built,
            parent_degree=10,
            max_total_nodes=1000,
            max_work=20_000_000_000,
        )
        self.assertTrue(certificate.admitted)
        self.assertEqual(certificate.node_upper_bounds, (252,))

    def test_execution_record_is_audited_against_each_reservation(self):
        certificate = admit(request())
        recorded = record_crx1_image_si_execution(
            certificate,
            (CRX1ImageSIExecution("exact_intersection_coset", 100, 500),),
            complete=True,
        )
        self.assertTrue(recorded.complete)
        self.assertEqual(recorded.executed_request_count, 1)
        self.assertEqual(recorded.search_nodes_used, 100)
        self.assertEqual(recorded.work_units_used, 500)

        with self.assertRaisesRegex(ValueError, "nodes exceed"):
            record_crx1_image_si_execution(
                certificate,
                (CRX1ImageSIExecution("empty_intersection", 176, 500),),
                complete=True,
            )
        with self.assertRaisesRegex(ValueError, "exact recursive-intersection status"):
            record_crx1_image_si_execution(
                certificate,
                (CRX1ImageSIExecution("undetermined_node_limit", 100, 500),),
                complete=True,
            )

    def test_complete_record_cannot_omit_a_reserved_request(self):
        certificate = admit(request(), request(left=2, right=12, setup=7, per_node=3))
        with self.assertRaisesRegex(ValueError, "omitted"):
            record_crx1_image_si_execution(
                certificate,
                (CRX1ImageSIExecution("empty_intersection", 100, 500),),
                complete=True,
            )

    def test_empty_cover_is_not_a_solution_certificate(self):
        certificate = admit()
        self.assertFalse(certificate.admitted)
        self.assertEqual(certificate.status, "crx1_image_si_empty_request_cover")


if __name__ == "__main__":
    unittest.main()
