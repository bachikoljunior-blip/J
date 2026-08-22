import unittest
from dataclasses import dataclass, replace

from corrected_soj_zero_aux_terminal_accounting_v1 import (
    SUCCESS_STATUS,
    compose_corrected_soj_zero_aux_terminal_accounting,
    replay_corrected_soj_zero_aux_terminal_accounting,
)


@dataclass(frozen=True)
class PublishedTransition:
    status: str = "certified_corrected_soj_small_part_reduction"
    transition_kind: str = "small_part_reduction"
    theorem_input_gate: bool = True
    canonical: bool = True
    exact: bool = True
    progress_certified: bool = True
    multiplicative_cost: float = 4.0
    max_multiplicative_cost: float = 8.0
    small_size_before: int = 12
    small_size_after: int = 0
    alpha: float = 0.75


def compose(t=PublishedTransition(), **kw):
    args = dict(
        root_n=32,
        terminal_semantics_certified=True,
        transition_cost_bound_certified=True,
    )
    args.update(kw)
    return compose_corrected_soj_zero_aux_terminal_accounting(t, **args)


class Rev285ZeroAuxTerminalAccountingTests(unittest.TestCase):
    def test_success_is_terminal_at_pre_transition_measure(self):
        out = compose()
        self.assertTrue(out.certified)
        self.assertEqual(out.status, SUCCESS_STATUS)
        self.assertEqual(out.accounting_root.n, 32)
        self.assertEqual(out.accounting_root.m, 12)
        self.assertEqual(out.accounting_root.children, ())
        self.assertTrue(out.accounting_root.terminal_certified)
        self.assertAlmostEqual(out.charged_log2_transition_cost, 3.0)
        self.assertTrue(out.validation.certified)
        self.assertEqual(out.validation.nodes_checked, 1)

    def test_zero_output_alone_is_not_terminal_semantics_proof(self):
        out = compose(terminal_semantics_certified=False)
        self.assertFalse(out.certified)
        self.assertIn("terminal-semantics", out.reason)

    def test_cost_bound_needs_external_mechanical_certificate(self):
        out = compose(transition_cost_bound_certified=False)
        self.assertFalse(out.certified)
        self.assertIn("mechanically certified", out.reason)

    def test_nonzero_output_is_not_silently_coerced(self):
        out = compose(replace(PublishedTransition(), small_size_after=1))
        self.assertFalse(out.certified)
        self.assertIn("small_size_after == 0", out.reason)

    def test_published_transition_contract_is_revalidated(self):
        for field, value in (
            ("theorem_input_gate", False),
            ("canonical", False),
            ("exact", False),
            ("progress_certified", False),
        ):
            with self.subTest(field=field):
                out = compose(replace(PublishedTransition(), **{field: value}))
                self.assertFalse(out.certified)
        self.assertFalse(compose(replace(PublishedTransition(), status="bare_johnson_label")).certified)
        self.assertFalse(compose(replace(PublishedTransition(), transition_kind="johnson_embedding")).certified)

    def test_cost_arithmetic_is_fail_closed_and_upper_bound_is_charged(self):
        self.assertFalse(compose(replace(PublishedTransition(), multiplicative_cost=9.0)).certified)
        self.assertFalse(compose(replace(PublishedTransition(), multiplicative_cost=0.5)).certified)
        self.assertFalse(compose(replace(PublishedTransition(), max_multiplicative_cost=float("inf"))).certified)
        out = compose(replace(PublishedTransition(), multiplicative_cost=1.0, max_multiplicative_cost=16.0))
        self.assertTrue(out.certified)
        self.assertEqual(out.charged_log2_transition_cost, 4.0)

    def test_measures_and_alpha_are_revalidated(self):
        self.assertFalse(compose(replace(PublishedTransition(), small_size_before=0)).certified)
        self.assertFalse(compose(root_n=11).certified)
        self.assertFalse(compose(replace(PublishedTransition(), alpha=0.5)).certified)
        self.assertFalse(compose(replace(PublishedTransition(), alpha=1.0)).certified)

    def test_main_quasipoly_envelope_can_reject_terminal_charge(self):
        huge = replace(PublishedTransition(), multiplicative_cost=2.0**20, max_multiplicative_cost=2.0**20)
        out = compose(huge, quasipoly_constant=1e-9)
        self.assertFalse(out.certified)
        self.assertIsNotNone(out.validation)
        self.assertEqual(out.validation.status, "quasipolynomial_bound_exceeded")

    def test_replay_binds_transition_and_parameters(self):
        t = PublishedTransition()
        out = compose(t)
        self.assertTrue(replay_corrected_soj_zero_aux_terminal_accounting(
            out,
            t,
            root_n=32,
            terminal_semantics_certified=True,
            transition_cost_bound_certified=True,
        ))
        self.assertFalse(replay_corrected_soj_zero_aux_terminal_accounting(
            out,
            replace(t, max_multiplicative_cost=16.0),
            root_n=32,
            terminal_semantics_certified=True,
            transition_cost_bound_certified=True,
        ))
        self.assertFalse(replay_corrected_soj_zero_aux_terminal_accounting(
            out,
            t,
            root_n=33,
            terminal_semantics_certified=True,
            transition_cost_bound_certified=True,
        ))

    def test_missing_structural_field_fails_closed(self):
        class Missing:
            status = "certified_corrected_soj_small_part_reduction"
        out = compose(Missing())
        self.assertFalse(out.certified)
        self.assertIn("missing required field", out.reason)


if __name__ == "__main__":
    unittest.main()
