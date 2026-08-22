from __future__ import annotations

from dataclasses import replace
from itertools import combinations
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
REV287 = HERE.parent / "2026-08-22_1155_JST"
for directory in (HERE, REV287):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from corrected_soj_johnson_relational_reduction_v1 import (  # noqa: E402
    certify_johnson_ground_relational_reduction,
)
from soj_child_semantic_reduction_binding_v1 import (  # noqa: E402
    certify_johnson_child_semantic_reduction,
    replay_johnson_child_semantic_reduction,
    verify_ground_candidate_parent_transport,
)


def embedding(v: int, k: int):
    return tuple(combinations(range(v), k))


def ground_transposition(v: int, a: int, b: int):
    out = list(range(v))
    out[a], out[b] = out[b], out[a]
    return tuple(out)


def ground_cycle(v: int):
    return tuple((i + 1) % v for i in range(v))


def induced_vertex_permutation(emb, ground_perm):
    index = {subset: i for i, subset in enumerate(emb)}
    return tuple(index[tuple(sorted(ground_perm[x] for x in subset))] for subset in emb)


def transport(values, perm):
    out = [None] * len(values)
    for source, target in enumerate(perm):
        out[target] = values[source]
    return tuple(out)


class Rev1900SemanticReductionTests(unittest.TestCase):
    def fixture(self, v=6, k=2):
        emb = embedding(v, k)
        ground_generators = (
            ground_transposition(v, 0, 1),
            ground_cycle(v),
        )
        ambient = tuple(induced_vertex_permutation(emb, gen) for gen in ground_generators)
        evidence = certify_johnson_ground_relational_reduction(
            johnson_ground_size=v,
            johnson_subset_size=k,
            embedding=emb,
            ambient_generators=ambient,
        )
        self.assertTrue(evidence.certified)
        return emb, ambient, evidence

    def test_certifies_replay_stable_child_projection(self):
        emb, ambient, evidence = self.fixture()
        source = tuple(("c", i % 4) for i in range(len(emb)))
        target = tuple(("t", (i * 3) % 5) for i in range(len(emb)))
        out = certify_johnson_child_semantic_reduction(
            reduction_evidence=evidence,
            johnson_ground_size=6,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=source,
            parent_target_values=target,
        )
        self.assertTrue(out.certified)
        self.assertTrue(out.canonical and out.replay_stable)
        self.assertTrue(out.parent_to_child_transport_certified)
        self.assertFalse(out.child_to_parent_transport_certified)
        self.assertFalse(out.parent_solution_equivalence_certified)
        self.assertEqual(len(out.child_source_values), 6)
        self.assertTrue(out.binding_identity.startswith("sha256:"))
        self.assertTrue(
            replay_johnson_child_semantic_reduction(
                out,
                reduction_evidence=evidence,
                johnson_ground_size=6,
                johnson_subset_size=2,
                embedding=emb,
                ambient_generators=ambient,
                parent_source_values=source,
                parent_target_values=target,
            )
        )

    def test_related_parent_strings_project_to_related_child_strings_and_filter_exactly(self):
        emb, ambient, evidence = self.fixture()
        source = tuple(i % 3 for i in range(len(emb)))
        p = ground_transposition(6, 2, 5)
        vertex_p = induced_vertex_permutation(evidence.canonical_vertex_subsets, p)
        target = transport(source, vertex_p)
        out = certify_johnson_child_semantic_reduction(
            reduction_evidence=evidence,
            johnson_ground_size=6,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=source,
            parent_target_values=target,
        )
        self.assertTrue(out.certified)
        self.assertEqual(transport(out.child_source_values, p), out.child_target_values)
        self.assertTrue(
            verify_ground_candidate_parent_transport(
                out,
                reduction_evidence=evidence,
                johnson_ground_size=6,
                johnson_subset_size=2,
                embedding=emb,
                ambient_generators=ambient,
                parent_source_values=source,
                parent_target_values=target,
                ground_permutation=p,
            )
        )
        self.assertFalse(
            verify_ground_candidate_parent_transport(
                out,
                reduction_evidence=evidence,
                johnson_ground_size=6,
                johnson_subset_size=2,
                embedding=emb,
                ambient_generators=ambient,
                parent_source_values=source,
                parent_target_values=target,
                ground_permutation=tuple(range(6)),
            )
        )

    def test_projection_deliberately_does_not_claim_converse(self):
        emb, ambient, evidence = self.fixture()
        cycle_edges = {tuple(sorted(edge)) for edge in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0))}
        two_triangles = {tuple(sorted(edge)) for edge in ((0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3))}
        source = tuple("red" if subset in cycle_edges else "blue" for subset in emb)
        target = tuple("red" if subset in two_triangles else "blue" for subset in emb)
        out = certify_johnson_child_semantic_reduction(
            reduction_evidence=evidence,
            johnson_ground_size=6,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=source,
            parent_target_values=target,
        )
        self.assertTrue(out.certified)
        self.assertEqual(out.child_source_values, out.child_target_values)
        self.assertFalse(out.child_to_parent_transport_certified)
        self.assertFalse(out.parent_solution_equivalence_certified)
        self.assertFalse(
            verify_ground_candidate_parent_transport(
                out,
                reduction_evidence=evidence,
                johnson_ground_size=6,
                johnson_subset_size=2,
                embedding=emb,
                ambient_generators=ambient,
                parent_source_values=source,
                parent_target_values=target,
                ground_permutation=tuple(range(6)),
            )
        )

    def test_rejects_tampered_rev287_reduction(self):
        emb, ambient, evidence = self.fixture()
        bad = replace(evidence, reduction_identity="sha256:" + "0" * 64)
        out = certify_johnson_child_semantic_reduction(
            reduction_evidence=bad,
            johnson_ground_size=6,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=(0,) * len(emb),
            parent_target_values=(0,) * len(emb),
        )
        self.assertFalse(out.certified)
        self.assertIn("replay", out.reason)

    def test_rejects_parent_dimension_mismatch(self):
        emb, ambient, evidence = self.fixture()
        out = certify_johnson_child_semantic_reduction(
            reduction_evidence=evidence,
            johnson_ground_size=6,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=(0,) * (len(emb) - 1),
            parent_target_values=(0,) * len(emb),
        )
        self.assertFalse(out.certified)
        self.assertIn("length", out.reason)

    def test_rejects_opaque_and_nonfinite_parent_values(self):
        emb, ambient, evidence = self.fixture()
        for bad in (object(), float("nan"), float("inf")):
            values = [0] * len(emb)
            values[0] = bad
            with self.subTest(value=type(bad).__name__):
                out = certify_johnson_child_semantic_reduction(
                    reduction_evidence=evidence,
                    johnson_ground_size=6,
                    johnson_subset_size=2,
                    embedding=emb,
                    ambient_generators=ambient,
                    parent_source_values=values,
                    parent_target_values=(0,) * len(emb),
                )
                self.assertFalse(out.certified)

    def test_value_freezing_is_type_strict_and_mapping_order_stable(self):
        emb, ambient, evidence = self.fixture(v=5, k=2)
        source_a = tuple({"b": [1, True], "a": None} for _ in emb)
        source_b = tuple({"a": None, "b": [1, True]} for _ in emb)
        target = tuple(0 for _ in emb)
        a = certify_johnson_child_semantic_reduction(
            reduction_evidence=evidence,
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=source_a,
            parent_target_values=target,
        )
        b = certify_johnson_child_semantic_reduction(
            reduction_evidence=evidence,
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=source_b,
            parent_target_values=target,
        )
        self.assertTrue(a.certified and b.certified)
        self.assertEqual(a.parent_source_digest, b.parent_source_digest)
        self.assertEqual(a.binding_identity, b.binding_identity)

        int_values = [0] * len(emb)
        bool_values = [0] * len(emb)
        int_values[0] = 1
        bool_values[0] = True
        c = certify_johnson_child_semantic_reduction(
            reduction_evidence=evidence,
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=int_values,
            parent_target_values=target,
        )
        d = certify_johnson_child_semantic_reduction(
            reduction_evidence=evidence,
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=bool_values,
            parent_target_values=target,
        )
        self.assertNotEqual(c.parent_source_digest, d.parent_source_digest)

    def test_binding_replay_rejects_tampering(self):
        emb, ambient, evidence = self.fixture(v=5, k=2)
        kwargs = dict(
            reduction_evidence=evidence,
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=tuple(i % 2 for i in range(len(emb))),
            parent_target_values=tuple(i % 3 for i in range(len(emb))),
        )
        out = certify_johnson_child_semantic_reduction(**kwargs)
        self.assertTrue(out.certified)
        self.assertFalse(
            replay_johnson_child_semantic_reduction(
                replace(out, child_source_digest="sha256:" + "0" * 64),
                **kwargs,
            )
        )

    def test_candidate_verifier_rejects_malformed_ground_permutation(self):
        emb, ambient, evidence = self.fixture(v=5, k=2)
        values = tuple(i for i in range(len(emb)))
        out = certify_johnson_child_semantic_reduction(
            reduction_evidence=evidence,
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=ambient,
            parent_source_values=values,
            parent_target_values=values,
        )
        self.assertTrue(out.certified)
        self.assertFalse(
            verify_ground_candidate_parent_transport(
                out,
                reduction_evidence=evidence,
                johnson_ground_size=5,
                johnson_subset_size=2,
                embedding=emb,
                ambient_generators=ambient,
                parent_source_values=values,
                parent_target_values=values,
                ground_permutation=(0, 1, 2, 3, 3),
            )
        )


if __name__ == "__main__":
    unittest.main()
