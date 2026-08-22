from __future__ import annotations

import unittest

from implicit_relation_image_resource_envelope_v2 import (
    implicit_relation_image_resource_envelope,
)


class ImplicitRelationImageResourceEnvelopeRev265Tests(unittest.TestCase):
    def make(self, **overrides):
        params = dict(
            original_root_degree=16,
            domain_degree=8,
            auxiliary_degree=12,
            generator_count=3,
            domain_order_upper_bound=64,
            image_order_upper_bound=8,
            image_order_poly_power=3,
            max_image_order=4096,
            max_work=10**15,
        )
        params.update(overrides)
        return implicit_relation_image_resource_envelope(**params)

    def test_admits_complete_bounded_attempt(self):
        env = self.make()
        self.assertTrue(env.admitted)
        self.assertTrue(env.root_lift_certified)
        self.assertTrue(env.order_bounds_compatible)
        self.assertTrue(env.image_gate_certified)
        self.assertLessEqual(env.work_upper_bound, env.max_work)
        self.assertFalse(env.complete)

    def test_rejects_original_root_lift(self):
        self.assertEqual(
            self.make(original_root_degree=4).status,
            "implicit_relation_image_original_root_lift_unavailable",
        )

    def test_rejects_image_gate(self):
        self.assertEqual(
            self.make(
                original_root_degree=8,
                domain_order_upper_bound=64,
                image_order_upper_bound=64,
                image_order_poly_power=1,
            ).status,
            "implicit_relation_image_order_gate_exceeded",
        )

    def test_rejects_finite_work_cap(self):
        env = self.make(max_work=100)
        self.assertFalse(env.admitted)
        self.assertEqual(env.work_upper_bound, 101)
        self.assertEqual(env.status, "implicit_relation_image_work_cap_exceeded")

    def test_saturates_at_arbitrary_precision_cap_plus_one(self):
        cap = 10**120
        env = self.make(
            domain_order_upper_bound=2**400,
            image_order_upper_bound=2**200,
            original_root_degree=2**80,
            image_order_poly_power=4,
            max_image_order=2**300,
            max_work=cap,
        )
        self.assertEqual(env.work_upper_bound, cap + 1)
        self.assertFalse(env.admitted)

    def test_rejects_image_bound_above_domain_bound(self):
        with self.assertRaises(ValueError):
            self.make(domain_order_upper_bound=8, image_order_upper_bound=16)

    def test_work_is_monotone_in_image_bound(self):
        self.assertLessEqual(
            self.make(image_order_upper_bound=4).work_upper_bound,
            self.make(image_order_upper_bound=8).work_upper_bound,
        )

    def test_work_is_monotone_in_generator_count(self):
        self.assertLessEqual(
            self.make(generator_count=2).work_upper_bound,
            self.make(generator_count=5).work_upper_bound,
        )

    def test_exact_gate_boundary_is_admitted(self):
        env = self.make(
            original_root_degree=8,
            auxiliary_degree=16,
            domain_order_upper_bound=512,
            image_order_upper_bound=512,
            image_order_poly_power=3,
            max_image_order=512,
            max_work=10**18,
        )
        self.assertTrue(env.image_gate_certified)
        self.assertTrue(env.admitted)

    def test_parameter_validation(self):
        for field in (
            "original_root_degree",
            "domain_degree",
            "auxiliary_degree",
            "generator_count",
            "domain_order_upper_bound",
            "image_order_upper_bound",
            "image_order_poly_power",
            "max_image_order",
            "max_work",
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.make(**{field: 0})

    def test_order_bounds_are_explicitly_compatible(self):
        self.assertTrue(self.make().order_bounds_compatible)

    def test_phase_reservation_is_explicit_and_sums_to_total_without_saturation(self):
        env = self.make()
        names = tuple(name for name, _ in env.phase_work_upper_bounds)
        self.assertEqual(
            names,
            (
                "induced_action",
                "domain_schreier",
                "image_schreier",
                "value_coset_intersection",
                "paired_preimage",
                "verification",
            ),
        )
        self.assertEqual(sum(work for _, work in env.phase_work_upper_bounds), env.work_upper_bound)


if __name__ == "__main__":
    unittest.main()
