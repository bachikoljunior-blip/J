from __future__ import annotations

from dataclasses import replace
import math
from types import SimpleNamespace
import unittest

from corrected_soj_johnson_terminal_cost_v1 import (
    CorrectedSOJJohnsonTerminalCostError,
    PrimitiveJohnsonGroundProof,
    RecurrenceAccountingNode,
    compose_corrected_soj_johnson_terminal_cost,
    replay_corrected_soj_johnson_terminal_cost,
)


ROOT_N = 64
CURRENT_DOMAIN = 12
GROUND = 5
SUBSET = 2
JOHNSON_SIZE = math.comb(GROUND, SUBSET)


def make_transition(**overrides):
    # Match the fields actually published by rev281 CorrectedSOJTransitionCertificate.
    # In particular, that certificate has neither current_domain_size nor proof_identity.
    values = dict(
        status="certified_corrected_soj_explicit_johnson_embedding",
        transition_kind="johnson_embedding",
        theorem_input_gate=True,
        canonical=True,
        exact=True,
        progress_certified=True,
        multiplicative_cost=4.0,
        max_multiplicative_cost=8.0,
        small_size_before=None,
        small_size_after=None,
        alpha=None,
        johnson_ground_size=GROUND,
        johnson_subset_size=SUBSET,
        johnson_vertex_count=JOHNSON_SIZE,
        reason="fixture corrected-SOJ explicit Johnson transition",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_terminal(**overrides):
    local = float(overrides.pop("local_log2_cost_bound", 10.0))
    root_n = int(overrides.get("root_n", ROOT_N))
    domain_size = int(overrides.get("domain_size", JOHNSON_SIZE))
    accounting = overrides.pop(
        "accounting",
        RecurrenceAccountingNode(
            n=root_n,
            m=domain_size,
            operation_kind="primitive_johnson_ground_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local,
            children=(),
            terminal_certified=True,
            reason="fixture exact primitive-Johnson terminal",
        ),
    )
    values = dict(
        status="exact_empty_primitive_johnson_ground",
        coset=None,
        operation_kind="primitive_johnson_ground_terminal",
        root_n=root_n,
        domain_size=domain_size,
        canonical=True,
        exact=True,
        local_cost_certified=True,
        local_log2_cost_bound=local,
        terminal_certified=True,
        children=(),
        accounting=accounting,
        permutation_candidates_checked=0,
        reason="fixture exact primitive-Johnson terminal",
        proof_identity="fixture-primitive-johnson-terminal",
        johnson_ground_size=GROUND,
        johnson_subset_size=SUBSET,
        ground_permutations_checked=120,
        recognition_search_nodes=3,
    )
    values.update(overrides)
    return PrimitiveJohnsonGroundProof(**values)


def compose(transition=None, terminal=None, **kwargs):
    params = dict(
        root_n=ROOT_N,
        current_domain_size=CURRENT_DOMAIN,
        transition_cost_bound_certified=True,
        terminal_admission_certified=True,
    )
    params.update(kwargs)
    return compose_corrected_soj_johnson_terminal_cost(
        make_transition() if transition is None else transition,
        make_terminal() if terminal is None else terminal,
        **params,
    )


class CorrectedSOJJohnsonTerminalCostTests(unittest.TestCase):
    def test_actual_rev281_shape_needs_no_legacy_fields(self):
        transition = make_transition()
        self.assertFalse(hasattr(transition, "current_domain_size"))
        self.assertFalse(hasattr(transition, "proof_identity"))
        certificate = compose(transition=transition)
        self.assertTrue(certificate.certified)
        self.assertEqual(certificate.current_domain_size, CURRENT_DOMAIN)
        self.assertEqual(len(certificate.transition.snapshot_identity), 64)

    def test_success_charges_certified_max_plus_terminal_and_uses_parent_measure(self):
        certificate = compose()
        self.assertTrue(certificate.certified)
        self.assertEqual(certificate.transition_log2_charge, 3.0)
        self.assertEqual(certificate.terminal_log2_charge, 10.0)
        self.assertEqual(certificate.accounting_root.local_log2_cost_bound, 13.0)
        self.assertEqual(certificate.accounting_root.m, CURRENT_DOMAIN)
        self.assertEqual(certificate.accounting_root.n, ROOT_N)
        self.assertTrue(certificate.accounting_root.terminal_certified)
        self.assertEqual(certificate.accounting_root.children, ())
        self.assertTrue(certificate.validation.certified)
        self.assertEqual(len(certificate.proof_identity), 64)

    def test_transition_snapshot_identity_is_deterministic_and_locally_derived(self):
        first = compose(transition=make_transition())
        second = compose(transition=make_transition())
        self.assertEqual(
            first.transition.snapshot_identity,
            second.transition.snapshot_identity,
        )
        changed = compose(transition=make_transition(reason="different reason"))
        self.assertNotEqual(
            first.transition.snapshot_identity,
            changed.transition.snapshot_identity,
        )

    def test_replay_succeeds_for_exact_same_inputs(self):
        transition = make_transition()
        terminal = make_terminal()
        certificate = compose(transition, terminal)
        self.assertTrue(
            replay_corrected_soj_johnson_terminal_cost(
                certificate,
                transition,
                terminal,
                root_n=ROOT_N,
                current_domain_size=CURRENT_DOMAIN,
                transition_cost_bound_certified=True,
                terminal_admission_certified=True,
            )
        )

    def test_replay_rejects_tampered_certificate(self):
        transition = make_transition()
        terminal = make_terminal()
        certificate = compose(transition, terminal)
        tampered = replace(certificate, proof_identity="0" * 64)
        self.assertFalse(
            replay_corrected_soj_johnson_terminal_cost(
                tampered,
                transition,
                terminal,
                root_n=ROOT_N,
                current_domain_size=CURRENT_DOMAIN,
                transition_cost_bound_certified=True,
                terminal_admission_certified=True,
            )
        )

    def test_replay_rejects_caller_measure_drift(self):
        transition = make_transition()
        terminal = make_terminal()
        certificate = compose(transition, terminal)
        self.assertFalse(
            replay_corrected_soj_johnson_terminal_cost(
                certificate,
                transition,
                terminal,
                root_n=ROOT_N,
                current_domain_size=CURRENT_DOMAIN + 1,
                transition_cost_bound_certified=True,
                terminal_admission_certified=True,
            )
        )

    def test_partial_johnson_embedding_is_rejected(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "full Johnson domain"
        ):
            compose(make_transition(johnson_vertex_count=JOHNSON_SIZE - 1))

    def test_nonshrinking_johnson_embedding_is_rejected(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "strictly reduce"
        ):
            compose(current_domain_size=JOHNSON_SIZE)

    def test_transition_cost_bound_requires_external_certificate(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "lacks an external/mechanical"
        ):
            compose(transition_cost_bound_certified=False)

    def test_terminal_admission_requires_external_certificate(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "admission must be certified"
        ):
            compose(terminal_admission_certified=False)

    def test_transition_actual_cost_may_not_exceed_certified_maximum(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "exceeds its certified maximum"
        ):
            compose(make_transition(multiplicative_cost=9.0, max_multiplicative_cost=8.0))

    def test_wrong_transition_status_is_rejected(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "status is not"
        ):
            compose(make_transition(status="certified_corrected_soj_small_part_reduction"))

    def test_terminal_ground_mismatch_is_rejected(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "ground/subset"
        ):
            compose(terminal=make_terminal(johnson_ground_size=6))

    def test_terminal_domain_mismatch_is_rejected(self):
        terminal = make_terminal(domain_size=JOHNSON_SIZE - 1)
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "domain size"
        ):
            compose(terminal=terminal)

    def test_nonexact_terminal_is_rejected(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "not canonical, exact"
        ):
            compose(terminal=make_terminal(exact=False))

    def test_exact_empty_terminal_may_not_carry_coset(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "must not carry a coset"
        ):
            compose(terminal=make_terminal(coset=object()))

    def test_terminal_accounting_mismatch_is_rejected(self):
        accounting = RecurrenceAccountingNode(
            n=ROOT_N,
            m=JOHNSON_SIZE,
            operation_kind="primitive_johnson_ground_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=9.0,
            children=(),
            terminal_certified=True,
            reason="understated fixture",
        )
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "proof/accounting leaf mismatch"
        ):
            compose(terminal=make_terminal(accounting=accounting))

    def test_parent_measure_must_fit_root_envelope(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "exceeds the root envelope"
        ):
            compose(current_domain_size=ROOT_N + 1)

    def test_current_domain_must_be_positive_integer(self):
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "positive integer"
        ):
            compose(current_domain_size=True)

    def test_combined_charge_must_fit_quasipolynomial_envelope(self):
        # At root_n=64 the primitive leaf charge 10 fits an allowed bound of
        # 0.0014 * 6^5 = 10.8864, while the composed charge 13 does not.
        with self.assertRaisesRegex(
            CorrectedSOJJohnsonTerminalCostError, "combined Johnson terminal"
        ):
            compose(quasipoly_constant=0.0014)


if __name__ == "__main__":
    unittest.main()
