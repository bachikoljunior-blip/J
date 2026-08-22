from __future__ import annotations

import copy
import pathlib
import sys
import unittest
from dataclasses import dataclass

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from soj_parent_filtered_result_accounting_coherence_v1 import (  # noqa: E402
    HANDOFF_STATUS,
    PARENT_EMPTY_STATUS,
    PARENT_NONEMPTY_STATUS,
    certify_parent_filtered_result_accounting_coherence,
    replay_parent_filtered_result_accounting_coherence,
)


def dg(ch: str) -> str:
    return "sha256:" + ch * 64


@dataclass
class Obj:
    pass


def base_parent(*, empty: bool = False) -> Obj:
    x = Obj()
    x.schema_version = 1
    x.status = PARENT_EMPTY_STATUS if empty else PARENT_NONEMPTY_STATUS
    x.certified = True
    x.exact = True
    x.complete = True
    x.reduction_identity = dg("1")
    x.semantic_binding_identity = dg("2")
    x.child_instance_identity = dg("3")
    x.child_result_identity = dg("4")
    x.action_degree = 4
    x.candidate_count = 24
    x.accepted_count = 0 if empty else 8
    x.representative = None if empty else (0, 1, 2, 3)
    x.parent_stabilizer_elements = () if empty else ((0, 1, 2, 3), (1, 0, 3, 2))
    x.work_bound = 313
    x.result_identity = dg("5")
    x.reason = "fixture"
    return x


def base_handoff() -> Obj:
    h = Obj()
    h.status = HANDOFF_STATUS
    h.certified = True
    h.handoff_digest = dg("6")
    h.charged_log2_reduction_cost = 7.0
    h.reduction = Obj()
    h.reduction.canonical = True
    h.reduction.exact = True
    h.reduction.progress_certified = True
    h.reduction.solution_transport_certified = True
    h.reduction.ambient_membership_transport_certified = True
    h.reduction.complement_ambiguity_handled = True
    h.reduction.source_action_degree = 6
    h.reduction.child_ground_size = 4
    h.reduction.johnson_ground_size = 4
    h.reduction.reduction_identity = dg("1")
    h.accounting_root = Obj()
    h.accounting_root.operation_kind = "aux_shrink"
    h.accounting_root.canonical = True
    h.accounting_root.cost_certified = True
    h.accounting_root.m = 6
    edge = Obj()
    edge.multiplicity = 1
    edge.node = Obj()
    edge.node.m = 4
    h.accounting_root.children = (edge,)
    h.validation = Obj()
    h.validation.certified = True
    return h


class Rev2400Tests(unittest.TestCase):
    def bind(self, parent=None, handoff=None, **kwargs):
        return certify_parent_filtered_result_accounting_coherence(
            base_parent() if parent is None else parent,
            base_handoff() if handoff is None else handoff,
            parent_result_replay_verified=kwargs.pop("parent_result_replay_verified", True),
            recursive_handoff_replay_verified=kwargs.pop("recursive_handoff_replay_verified", True),
        )

    def test_nonempty_success_and_replay(self):
        p, h = base_parent(), base_handoff()
        c = self.bind(p, h)
        self.assertTrue(c.certified)
        self.assertEqual(c.outcome_kind, "nonempty")
        self.assertEqual(c.parent_filter_work_bound, 313)
        self.assertEqual(c.charged_log2_reduction_cost, 7.0)
        self.assertTrue(replay_parent_filtered_result_accounting_coherence(
            c, p, h, parent_result_replay_verified=True, recursive_handoff_replay_verified=True
        ))

    def test_exact_empty_success(self):
        c = self.bind(base_parent(empty=True), base_handoff())
        self.assertTrue(c.certified)
        self.assertEqual(c.outcome_kind, "exact_empty")
        self.assertEqual(c.accepted_count, 0)

    def test_parent_replay_gate_is_literal(self):
        self.assertFalse(self.bind(parent_result_replay_verified=1).certified)

    def test_handoff_replay_gate_is_literal(self):
        self.assertFalse(self.bind(recursive_handoff_replay_verified=1).certified)

    def test_reduction_identity_drift_fails(self):
        h = base_handoff(); h.reduction.reduction_identity = dg("9")
        self.assertFalse(self.bind(base_parent(), h).certified)

    def test_child_measure_drift_fails(self):
        h = base_handoff(); h.reduction.child_ground_size = 5; h.reduction.johnson_ground_size = 5; h.accounting_root.children[0].node.m = 5
        self.assertFalse(self.bind(base_parent(), h).certified)

    def test_handoff_requires_strict_shrink(self):
        h = base_handoff(); h.reduction.source_action_degree = 4; h.accounting_root.m = 4
        self.assertFalse(self.bind(base_parent(), h).certified)

    def test_handoff_accounting_child_must_match(self):
        h = base_handoff(); h.accounting_root.children[0].node.m = 3
        self.assertFalse(self.bind(base_parent(), h).certified)

    def test_handoff_exactly_one_recursive_child(self):
        h = base_handoff(); h.accounting_root.children = h.accounting_root.children * 2
        self.assertFalse(self.bind(base_parent(), h).certified)

    def test_nonempty_parent_requires_representative(self):
        p = base_parent(); p.representative = None
        self.assertFalse(self.bind(p, base_handoff()).certified)

    def test_empty_parent_cannot_carry_stabilizer(self):
        p = base_parent(empty=True); p.parent_stabilizer_elements = ((0, 1, 2, 3),)
        self.assertFalse(self.bind(p, base_handoff()).certified)

    def test_accepted_count_cannot_exceed_candidates(self):
        p = base_parent(); p.accepted_count = 25
        self.assertFalse(self.bind(p, base_handoff()).certified)

    def test_stabilizer_must_be_canonical_unique(self):
        p = base_parent(); p.parent_stabilizer_elements = ((1, 0, 3, 2), (0, 1, 2, 3))
        self.assertFalse(self.bind(p, base_handoff()).certified)

    def test_malformed_digest_fails(self):
        p = base_parent(); p.result_identity = "sha256:ABC"
        self.assertFalse(self.bind(p, base_handoff()).certified)

    def test_nonfinite_charge_fails(self):
        h = base_handoff(); h.charged_log2_reduction_cost = float("inf")
        self.assertFalse(self.bind(base_parent(), h).certified)

    def test_replay_detects_certificate_mutation(self):
        p, h = base_parent(), base_handoff()
        c = self.bind(p, h)
        mutated = copy.deepcopy(c)
        object.__setattr__(mutated, "parent_filter_work_bound", 314)
        self.assertFalse(replay_parent_filtered_result_accounting_coherence(
            mutated, p, h, parent_result_replay_verified=True, recursive_handoff_replay_verified=True
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
