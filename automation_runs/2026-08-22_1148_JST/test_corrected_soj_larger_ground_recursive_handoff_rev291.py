from __future__ import annotations

from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
MAIN = HERE.parent / "2026-08-19_0851_JST"
for path in (HERE, MAIN):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode  # noqa: E402
from corrected_soj_larger_ground_recursive_handoff_v1 import (  # noqa: E402
    compose_corrected_soj_larger_ground_recursive_handoff,
    replay_corrected_soj_larger_ground_recursive_handoff,
)


def ground_cap(**changes):
    data = dict(
        status="undetermined_johnson_ground_cap",
        operation_kind="primitive_johnson_ground_cap",
        root_n=64,
        domain_size=15,
        canonical=True,
        exact=False,
        local_cost_certified=False,
        terminal_certified=False,
        johnson_ground_size=6,
        johnson_subset_size=2,
    )
    data.update(changes)
    return SimpleNamespace(**data)


def reduction(**changes):
    data = dict(
        status="certified_johnson_ground_relational_reduction",
        canonical=True,
        exact=True,
        progress_certified=True,
        solution_transport_certified=True,
        ambient_membership_transport_certified=True,
        complement_ambiguity_handled=True,
        source_action_degree=15,
        johnson_ground_size=6,
        johnson_subset_size=2,
        child_ground_size=6,
        multiplicative_cost=4.0,
        max_multiplicative_cost=8.0,
        reduction_identity="sha256:" + "a" * 64,
    )
    data.update(changes)
    return SimpleNamespace(**data)


def child(**changes):
    data = dict(
        n=64,
        m=6,
        operation_kind="terminal_fixture",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=2.0,
        children=(),
        terminal_certified=True,
        reason="exact child fixture",
    )
    data.update(changes)
    return RecurrenceAccountingNode(**data)


class Rev291LargerGroundRecursiveHandoffTests(unittest.TestCase):
    def compose(self, g=None, r=None, c=None, **kwargs):
        return compose_corrected_soj_larger_ground_recursive_handoff(
            g or ground_cap(),
            r or reduction(),
            child_accounting=c or child(),
            reduction_cost_bound_certified=kwargs.pop("reduction_cost_bound_certified", True),
            **kwargs,
        )

    def test_certified_handoff_and_replay(self):
        g, r, c = ground_cap(), reduction(), child()
        out = self.compose(g, r, c)
        self.assertTrue(out.certified)
        self.assertEqual(out.status, "certified_corrected_soj_larger_ground_recursive_handoff")
        self.assertEqual(out.accounting_root.operation_kind, "aux_shrink")
        self.assertEqual((out.accounting_root.m, out.accounting_root.children[0].node.m), (15, 6))
        self.assertEqual(out.charged_log2_reduction_cost, 3.0)
        self.assertTrue(out.handoff_digest.startswith("sha256:"))
        self.assertTrue(
            replay_corrected_soj_larger_ground_recursive_handoff(
                out, g, r, child_accounting=c, reduction_cost_bound_certified=True
            )
        )

    def test_requires_exact_ground_cap_status(self):
        self.assertFalse(self.compose(g=ground_cap(status="exact_primitive_johnson_ground_coset")).certified)

    def test_rejects_ground_cap_that_claims_exactness(self):
        self.assertFalse(self.compose(g=ground_cap(exact=True)).certified)
        self.assertFalse(self.compose(g=ground_cap(local_cost_certified=True)).certified)
        self.assertFalse(self.compose(g=ground_cap(terminal_certified=True)).certified)

    def test_rejects_noncanonical_ground_cap(self):
        self.assertFalse(self.compose(g=ground_cap(canonical=False)).certified)

    def test_reconstructs_action_degree_from_johnson_parameters(self):
        out = self.compose(g=ground_cap(domain_size=14), r=reduction(source_action_degree=14))
        self.assertFalse(out.certified)
        self.assertIn("reconstruct", out.reason)

    def test_rejects_malformed_johnson_parameters(self):
        self.assertFalse(self.compose(g=ground_cap(johnson_subset_size=1)).certified)
        self.assertFalse(self.compose(g=ground_cap(johnson_ground_size=3, domain_size=3)).certified)

    def test_rejects_non_strict_ground_boolean(self):
        out = self.compose(g=ground_cap(canonical=1))
        self.assertFalse(out.certified)
        self.assertIn("strict boolean", out.reason)

    def test_requires_exact_canonical_progress_reduction(self):
        for field in ("canonical", "exact", "progress_certified"):
            with self.subTest(field=field):
                self.assertFalse(self.compose(r=reduction(**{field: False})).certified)

    def test_requires_solution_and_membership_transport(self):
        self.assertFalse(self.compose(r=reduction(solution_transport_certified=False)).certified)
        self.assertFalse(self.compose(r=reduction(ambient_membership_transport_certified=False)).certified)

    def test_requires_explicit_complement_handling(self):
        out = self.compose(r=reduction(complement_ambiguity_handled=False))
        self.assertFalse(out.certified)
        self.assertIn("complement", out.reason.lower())

    def test_requires_parameter_and_degree_binding(self):
        self.assertFalse(self.compose(r=reduction(source_action_degree=16)).certified)
        self.assertFalse(self.compose(r=reduction(johnson_ground_size=7)).certified)
        self.assertFalse(self.compose(r=reduction(johnson_subset_size=3)).certified)
        self.assertFalse(self.compose(r=reduction(child_ground_size=5)).certified)

    def test_rejects_uncertified_or_underbounded_cost(self):
        self.assertFalse(self.compose(reduction_cost_bound_certified=False).certified)
        self.assertFalse(self.compose(r=reduction(multiplicative_cost=9.0, max_multiplicative_cost=8.0)).certified)
        self.assertFalse(self.compose(r=reduction(multiplicative_cost=float("nan"))).certified)
        self.assertFalse(self.compose(r=reduction(max_multiplicative_cost=float("inf"))).certified)

    def test_rejects_noncanonical_reduction_digest(self):
        self.assertFalse(self.compose(r=reduction(reduction_identity="not-a-digest")).certified)
        self.assertFalse(self.compose(r=reduction(reduction_identity="sha256:" + "A" * 64)).certified)

    def test_child_measure_must_bind_root_and_ground(self):
        self.assertFalse(self.compose(c=child(n=63)).certified)
        self.assertFalse(self.compose(c=child(m=5)).certified)

    def test_configured_shrink_is_enforced(self):
        out = self.compose(shrink_fraction=0.39)
        self.assertFalse(out.certified)
        self.assertIn("shrink", out.reason.lower())

    def test_main_recurrence_validation_remains_fail_closed(self):
        out = self.compose(c=child(cost_certified=False))
        self.assertFalse(out.certified)
        self.assertEqual(out.status, "corrected_soj_larger_ground_recurrence_rejected")
        self.assertIsNotNone(out.validation)
        self.assertFalse(out.validation.certified)

    def test_replay_detects_evidence_change(self):
        g, r, c = ground_cap(), reduction(), child()
        out = self.compose(g, r, c)
        changed = reduction(reduction_identity="sha256:" + "b" * 64)
        self.assertFalse(
            replay_corrected_soj_larger_ground_recursive_handoff(
                out, g, changed, child_accounting=c, reduction_cost_bound_certified=True
            )
        )


if __name__ == "__main__":
    unittest.main()
