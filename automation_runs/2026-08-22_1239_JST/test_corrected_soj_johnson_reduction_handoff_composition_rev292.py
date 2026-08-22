from __future__ import annotations

import hashlib
import json
from itertools import combinations
from math import comb, log2
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from corrected_soj_johnson_reduction_handoff_composition_v1 import (  # noqa: E402
    certify_johnson_reduction_handoff_composition,
    replay_johnson_reduction_handoff_composition,
)


def sha(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def construction(**changes):
    v, k = 6, 2
    subsets = tuple(combinations(range(v), k))
    stars = tuple(
        tuple(index for index, subset in enumerate(subsets) if point in subset)
        for point in range(v)
    )
    generators = (
        tuple(range(v)),
        tuple((point + 1) % v for point in range(v)),
    )
    n = comb(v, k)
    data = dict(
        schema_version=1,
        status="certified_johnson_ground_relational_reduction",
        certified=True,
        canonical=True,
        exact=True,
        progress_certified=True,
        solution_transport_certified=True,
        ambient_membership_transport_certified=True,
        complement_ambiguity_handled=True,
        source_action_degree=n,
        johnson_ground_size=v,
        johnson_subset_size=k,
        child_ground_size=v,
        multiplicative_cost=1.0,
        max_multiplicative_cost=1.0,
        reduction_identity="sha256:" + "a" * 64,
        canonical_vertex_subsets=subsets,
        canonical_ground_stars=stars,
        induced_ground_generators=generators,
        construction_work_bound=(2 + 2 * len(generators)) * n * k
        + len(generators) * n
        + v,
        reason="fixture",
    )
    data.update(changes)
    return SimpleNamespace(**data)


def accounting_child(**changes):
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
    return SimpleNamespace(**data)


def handoff(c=None, **changes):
    c = c or construction()
    ground = SimpleNamespace(
        status="undetermined_johnson_ground_cap",
        operation_kind="primitive_johnson_ground_cap",
        root_n=64,
        domain_size=c.source_action_degree,
        canonical=True,
        exact=False,
        local_cost_certified=False,
        terminal_certified=False,
        johnson_ground_size=c.johnson_ground_size,
        johnson_subset_size=c.johnson_subset_size,
    )
    reduction = SimpleNamespace(
        status=c.status,
        canonical=c.canonical,
        exact=c.exact,
        progress_certified=c.progress_certified,
        solution_transport_certified=c.solution_transport_certified,
        ambient_membership_transport_certified=(
            c.ambient_membership_transport_certified
        ),
        complement_ambiguity_handled=c.complement_ambiguity_handled,
        source_action_degree=c.source_action_degree,
        johnson_ground_size=c.johnson_ground_size,
        johnson_subset_size=c.johnson_subset_size,
        child_ground_size=c.child_ground_size,
        multiplicative_cost=c.multiplicative_cost,
        max_multiplicative_cost=c.max_multiplicative_cost,
        reduction_identity=c.reduction_identity,
    )
    child = accounting_child(m=c.child_ground_size)
    edge = SimpleNamespace(node=child, multiplicity=1)
    charge = log2(c.max_multiplicative_cost)
    root = SimpleNamespace(
        n=ground.root_n,
        m=ground.domain_size,
        operation_kind="aux_shrink",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=charge,
        children=(edge,),
        terminal_certified=False,
        reason="certified exact Johnson handoff",
    )
    work = charge + child.local_log2_cost_bound
    allowed = 64.0 * (log2(ground.root_n) ** 5)
    validation = SimpleNamespace(
        status="certified_quasipolynomial_recurrence",
        certified=True,
        log2_work_bound=work,
        allowed_log2_work=allowed,
        nodes_checked=2,
        max_depth=1,
        reason="fixture",
    )
    digest = sha(
        {
            "schema_version": 1,
            "ground_cap": dict(vars(ground)),
            "reduction": dict(vars(reduction)),
            "child_measure": [child.n, child.m],
            "child_operation_kind": child.operation_kind,
            "charged_log2_reduction_cost": float(charge),
            "shrink_fraction": 0.9,
        }
    )
    data = dict(
        schema_version=1,
        status="certified_corrected_soj_larger_ground_recursive_handoff",
        certified=True,
        ground_cap=ground,
        reduction=reduction,
        accounting_root=root,
        validation=validation,
        charged_log2_reduction_cost=charge,
        handoff_digest=digest,
        reason="fixture",
    )
    data.update(changes)
    return SimpleNamespace(**data)


class Rev292JohnsonReductionHandoffCompositionTests(unittest.TestCase):
    def test_certified_composition_and_replay(self):
        c = construction()
        h = handoff(c)
        out = certify_johnson_reduction_handoff_composition(c, h)
        self.assertTrue(out.certified, out.reason)
        self.assertEqual(
            out.status,
            "certified_johnson_reduction_handoff_composition",
        )
        self.assertEqual(out.construction.reduction_identity, c.reduction_identity)
        self.assertEqual(out.handoff.source_action_degree, 15)
        self.assertTrue(out.composition_digest.startswith("sha256:"))
        self.assertTrue(
            replay_johnson_reduction_handoff_composition(out, c, h)
        )

    def test_requires_certified_construction(self):
        out = certify_johnson_reduction_handoff_composition(
            construction(certified=False),
            handoff(),
        )
        self.assertFalse(out.certified)
        self.assertIn("not certified", out.reason)

    def test_rejects_non_strict_construction_boolean(self):
        out = certify_johnson_reduction_handoff_composition(
            construction(canonical=1),
            handoff(),
        )
        self.assertFalse(out.certified)
        self.assertIn("strict boolean", out.reason)

    def test_rejects_incomplete_johnson_embedding(self):
        c = construction()
        out = certify_johnson_reduction_handoff_composition(
            construction(
                canonical_vertex_subsets=c.canonical_vertex_subsets[:-1]
            ),
            handoff(c),
        )
        self.assertFalse(out.certified)
        self.assertIn("length", out.reason)

    def test_rejects_star_incidence_mismatch(self):
        c = construction()
        stars = list(c.canonical_ground_stars)
        stars[0], stars[1] = stars[1], stars[0]
        out = certify_johnson_reduction_handoff_composition(
            construction(canonical_ground_stars=tuple(stars)),
            handoff(c),
        )
        self.assertFalse(out.certified)
        self.assertIn("incidence", out.reason)

    def test_rejects_nonpermutation_ground_generator(self):
        c = construction()
        bad = list(c.induced_ground_generators)
        bad[0] = (0, 0, 1, 2, 3, 4)
        out = certify_johnson_reduction_handoff_composition(
            construction(induced_ground_generators=tuple(bad)),
            handoff(c),
        )
        self.assertFalse(out.certified)
        self.assertIn("not a permutation", out.reason)

    def test_rejects_incorrect_construction_work_bound(self):
        c = construction()
        out = certify_johnson_reduction_handoff_composition(
            construction(
                construction_work_bound=c.construction_work_bound + 1
            ),
            handoff(c),
        )
        self.assertFalse(out.certified)
        self.assertIn("work_bound", out.reason)

    def test_binds_every_shared_reduction_field(self):
        cases = {
            "canonical": False,
            "source_action_degree": 14,
            "johnson_ground_size": 7,
            "johnson_subset_size": 3,
            "child_ground_size": 5,
            "multiplicative_cost": 2.0,
            "max_multiplicative_cost": 2.0,
            "reduction_identity": "sha256:" + "b" * 64,
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                c = construction()
                h = handoff(c)
                setattr(h.reduction, field, value)
                out = certify_johnson_reduction_handoff_composition(c, h)
                self.assertFalse(out.certified)
                self.assertIn(field, out.reason)

    def test_rejects_uncertified_handoff(self):
        c = construction()
        out = certify_johnson_reduction_handoff_composition(
            c,
            handoff(c, certified=False),
        )
        self.assertFalse(out.certified)
        self.assertIn("not a certified", out.reason)

    def test_replays_handoff_digest(self):
        c = construction()
        h = handoff(c, handoff_digest="sha256:" + "f" * 64)
        out = certify_johnson_reduction_handoff_composition(c, h)
        self.assertFalse(out.certified)
        self.assertIn("does not replay", out.reason)

    def test_rejects_wrong_accounting_source_measure(self):
        c = construction()
        h = handoff(c)
        h.accounting_root.m = 14
        out = certify_johnson_reduction_handoff_composition(c, h)
        self.assertFalse(out.certified)
        self.assertIn("source degree", out.reason)

    def test_rejects_wrong_recursive_child_measure(self):
        c = construction()
        h = handoff(c)
        h.accounting_root.children[0].node.m = 5
        out = certify_johnson_reduction_handoff_composition(c, h)
        self.assertFalse(out.certified)
        self.assertIn("constructed ground", out.reason)

    def test_rejects_insufficient_auxiliary_shrink(self):
        c = construction()
        h = handoff(c)
        out = certify_johnson_reduction_handoff_composition(
            c,
            h,
            shrink_fraction=0.39,
        )
        self.assertFalse(out.certified)
        self.assertIn("shrink", out.reason)

    def test_rejects_validation_work_mismatch(self):
        c = construction()
        h = handoff(c)
        h.validation.log2_work_bound += 1.0
        out = certify_johnson_reduction_handoff_composition(c, h)
        self.assertFalse(out.certified)
        self.assertIn("work bound", out.reason)

    def test_rejects_validation_shape_mismatch(self):
        c = construction()
        h = handoff(c)
        h.validation.nodes_checked = 3
        out = certify_johnson_reduction_handoff_composition(c, h)
        self.assertFalse(out.certified)
        self.assertIn("node/depth", out.reason)

    def test_rejects_accounting_cycle(self):
        c = construction()
        h = handoff(c)
        edge = SimpleNamespace(node=h.accounting_root, multiplicity=1)
        h.accounting_root.children = (edge,)
        out = certify_johnson_reduction_handoff_composition(c, h)
        self.assertFalse(out.certified)
        self.assertIn("cycle", out.reason)

    def test_rejects_nonfinite_cost(self):
        c = construction(max_multiplicative_cost=float("nan"))
        out = certify_johnson_reduction_handoff_composition(c, handoff())
        self.assertFalse(out.certified)
        self.assertIn("finite real", out.reason)

    def test_replay_detects_construction_change(self):
        c = construction()
        h = handoff(c)
        out = certify_johnson_reduction_handoff_composition(c, h)
        changed = construction(
            reduction_identity="sha256:" + "b" * 64
        )
        self.assertFalse(
            replay_johnson_reduction_handoff_composition(out, changed, h)
        )


if __name__ == "__main__":
    unittest.main()
