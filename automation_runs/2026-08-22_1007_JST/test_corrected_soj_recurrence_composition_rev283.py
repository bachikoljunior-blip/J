from pathlib import Path
from types import SimpleNamespace
import dataclasses
import sys
import unittest

HERE = Path(__file__).resolve().parent
MAIN_RUN = HERE.parent / "2026-08-19_0851_JST"
for path in (HERE, MAIN_RUN):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from corrected_soj_recurrence_composition_v1 import (
    compose_corrected_soj_small_part_recurrence,
    replay_corrected_soj_recurrence_composition,
)


def transition(**overrides):
    data = dict(
        status="certified_corrected_soj_small_part_reduction",
        transition_kind="small_part_reduction",
        theorem_input_gate=True,
        canonical=True,
        exact=True,
        progress_certified=True,
        multiplicative_cost=4.0,
        max_multiplicative_cost=8.0,
        small_size_before=10,
        small_size_after=6,
        alpha=0.7,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def terminal(*, n=100, m=6, canonical=True, cost_certified=True, cost=1.0):
    return RecurrenceAccountingNode(
        n=n,
        m=m,
        operation_kind="terminal",
        canonical=canonical,
        cost_certified=cost_certified,
        local_log2_cost_bound=cost,
        children=(),
        terminal_certified=True,
        reason="fixture exact terminal",
    )


class CorrectedSOJRecurrenceCompositionRev283Tests(unittest.TestCase):
    def test_certified_small_part_transition_composes(self):
        child = terminal()
        got = compose_corrected_soj_small_part_recurrence(
            transition(),
            root_n=100,
            child_accounting=child,
            transition_cost_bound_certified=True,
            branch_multiplicity=3,
        )
        self.assertTrue(got.certified)
        self.assertEqual(got.status, "certified_corrected_soj_recurrence_composition")
        self.assertEqual(got.accounting_root.operation_kind, "aux_shrink")
        self.assertEqual(got.accounting_root.m, 10)
        self.assertEqual(got.accounting_root.children[0].node.m, 6)
        self.assertEqual(got.accounting_root.children[0].multiplicity, 3)
        self.assertEqual(got.charged_log2_transition_cost, 3.0)
        self.assertTrue(got.validation.certified)
        self.assertTrue(
            replay_corrected_soj_recurrence_composition(
                got,
                transition(),
                root_n=100,
                child_accounting=child,
                transition_cost_bound_certified=True,
                branch_multiplicity=3,
            )
        )

    def test_johnson_embedding_is_not_misclassified_as_aux_shrink(self):
        got = compose_corrected_soj_small_part_recurrence(
            transition(
                status="certified_corrected_soj_explicit_johnson_embedding",
                transition_kind="johnson_embedding",
            ),
            root_n=100,
            child_accounting=terminal(),
            transition_cost_bound_certified=True,
        )
        self.assertFalse(got.certified)
        self.assertIn("only the certified constant-factor", got.reason)

    def test_transition_gate_exactness_and_canonicality_are_rechecked(self):
        for patch in (
            {"theorem_input_gate": False},
            {"canonical": False},
            {"exact": False},
            {"progress_certified": False},
        ):
            with self.subTest(patch=patch):
                got = compose_corrected_soj_small_part_recurrence(
                    transition(**patch),
                    root_n=100,
                    child_accounting=terminal(),
                    transition_cost_bound_certified=True,
                )
                self.assertFalse(got.certified)

    def test_transition_constant_factor_arithmetic_is_rechecked(self):
        got = compose_corrected_soj_small_part_recurrence(
            transition(small_size_after=7, alpha=0.7),
            root_n=100,
            child_accounting=terminal(m=7),
            transition_cost_bound_certified=True,
        )
        self.assertFalse(got.certified)
        self.assertIn("constant-factor", got.reason)

    def test_global_shrink_fraction_must_dominate_transition_alpha(self):
        got = compose_corrected_soj_small_part_recurrence(
            transition(alpha=0.8, small_size_after=7),
            root_n=100,
            child_accounting=terminal(m=7),
            transition_cost_bound_certified=True,
            shrink_fraction=0.75,
        )
        self.assertFalse(got.certified)
        self.assertIn("weaker than", got.reason)

    def test_local_cost_certificate_is_not_manufactured(self):
        got = compose_corrected_soj_small_part_recurrence(
            transition(),
            root_n=100,
            child_accounting=terminal(),
            transition_cost_bound_certified=False,
        )
        self.assertFalse(got.certified)
        self.assertIn("does not manufacture", got.reason)

    def test_multiplicative_cost_bound_is_charged_and_checked(self):
        got = compose_corrected_soj_small_part_recurrence(
            transition(multiplicative_cost=9.0, max_multiplicative_cost=8.0),
            root_n=100,
            child_accounting=terminal(),
            transition_cost_bound_certified=True,
        )
        self.assertFalse(got.certified)
        self.assertIn("exceeds", got.reason)

    def test_child_measure_must_match_transition_output(self):
        got = compose_corrected_soj_small_part_recurrence(
            transition(),
            root_n=100,
            child_accounting=terminal(m=5),
            transition_cost_bound_certified=True,
        )
        self.assertFalse(got.certified)
        self.assertIn("does not equal", got.reason)

    def test_nonpositive_branch_multiplicity_fails_closed(self):
        got = compose_corrected_soj_small_part_recurrence(
            transition(),
            root_n=100,
            child_accounting=terminal(),
            transition_cost_bound_certified=True,
            branch_multiplicity=0,
        )
        self.assertFalse(got.certified)
        self.assertIn("multiplicity", got.reason)

    def test_invalid_child_recurrence_remains_fail_closed(self):
        got = compose_corrected_soj_small_part_recurrence(
            transition(),
            root_n=100,
            child_accounting=terminal(canonical=False),
            transition_cost_bound_certified=True,
        )
        self.assertFalse(got.certified)
        self.assertIsNotNone(got.validation)
        self.assertEqual(got.validation.status, "noncanonical_accounting_step")

    def test_zero_auxiliary_output_is_not_silently_normalized(self):
        got = compose_corrected_soj_small_part_recurrence(
            transition(small_size_after=0),
            root_n=100,
            child_accounting=terminal(m=1),
            transition_cost_bound_certified=True,
        )
        self.assertFalse(got.certified)
        self.assertIn("positive strictly smaller", got.reason)

    def test_replay_detects_transition_or_child_drift(self):
        child = terminal()
        got = compose_corrected_soj_small_part_recurrence(
            transition(),
            root_n=100,
            child_accounting=child,
            transition_cost_bound_certified=True,
        )
        self.assertTrue(got.certified)
        self.assertFalse(
            replay_corrected_soj_recurrence_composition(
                got,
                transition(max_multiplicative_cost=16.0),
                root_n=100,
                child_accounting=child,
                transition_cost_bound_certified=True,
            )
        )
        drifted_child = dataclasses.replace(child, local_log2_cost_bound=2.0)
        self.assertFalse(
            replay_corrected_soj_recurrence_composition(
                got,
                transition(),
                root_n=100,
                child_accounting=drifted_child,
                transition_cost_bound_certified=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
