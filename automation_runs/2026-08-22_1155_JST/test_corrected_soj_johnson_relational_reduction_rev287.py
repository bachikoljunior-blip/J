from __future__ import annotations

from dataclasses import replace
from itertools import combinations
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from corrected_soj_johnson_relational_reduction_v1 import (  # noqa: E402
    certify_johnson_ground_relational_reduction,
    replay_johnson_ground_relational_reduction,
)


def embedding(v: int, k: int):
    return tuple(combinations(range(v), k))


def induced_vertex_permutation(emb, ground_perm):
    index = {subset: i for i, subset in enumerate(emb)}
    return tuple(index[tuple(sorted(ground_perm[x] for x in subset))] for subset in emb)


def ground_transposition(v: int, a: int, b: int):
    out = list(range(v))
    out[a], out[b] = out[b], out[a]
    return tuple(out)


def ground_cycle(v: int):
    return tuple((i + 1) % v for i in range(v))


class Rev287JohnsonRelationalReductionTests(unittest.TestCase):
    def test_certifies_full_johnson_ground_action_and_replay(self):
        emb = embedding(6, 2)
        generators = (
            induced_vertex_permutation(emb, ground_transposition(6, 0, 1)),
            induced_vertex_permutation(emb, ground_cycle(6)),
        )
        out = certify_johnson_ground_relational_reduction(
            johnson_ground_size=6,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=generators,
        )
        self.assertTrue(out.certified)
        self.assertEqual(out.status, "certified_johnson_ground_relational_reduction")
        self.assertEqual((out.source_action_degree, out.child_ground_size), (15, 6))
        self.assertTrue(out.canonical and out.exact and out.progress_certified)
        self.assertTrue(out.solution_transport_certified)
        self.assertTrue(out.ambient_membership_transport_certified)
        self.assertTrue(out.complement_ambiguity_handled)
        self.assertEqual((out.multiplicative_cost, out.max_multiplicative_cost), (1.0, 1.0))
        self.assertTrue(out.reduction_identity.startswith("sha256:"))
        self.assertTrue(
            replay_johnson_ground_relational_reduction(
                out,
                johnson_ground_size=6,
                johnson_subset_size=2,
                embedding=emb,
                ambient_generators=generators,
            )
        )

    def test_ground_label_renaming_has_same_canonical_reduction_identity(self):
        emb = embedding(6, 2)
        gp = ground_cycle(6)
        generator = induced_vertex_permutation(emb, ground_transposition(6, 0, 2))
        relabeled = tuple(tuple(sorted(gp[x] for x in subset)) for subset in emb)
        out1 = certify_johnson_ground_relational_reduction(
            johnson_ground_size=6,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=(generator,),
        )
        out2 = certify_johnson_ground_relational_reduction(
            johnson_ground_size=6,
            johnson_subset_size=2,
            embedding=relabeled,
            ambient_generators=(generator,),
        )
        self.assertTrue(out1.certified and out2.certified)
        self.assertEqual(out1.reduction_identity, out2.reduction_identity)
        self.assertEqual(out1.canonical_vertex_subsets, out2.canonical_vertex_subsets)

    def test_generator_order_does_not_change_identity(self):
        emb = embedding(6, 2)
        g1 = induced_vertex_permutation(emb, ground_transposition(6, 0, 1))
        g2 = induced_vertex_permutation(emb, ground_cycle(6))
        a = certify_johnson_ground_relational_reduction(
            johnson_ground_size=6, johnson_subset_size=2, embedding=emb, ambient_generators=(g1, g2)
        )
        b = certify_johnson_ground_relational_reduction(
            johnson_ground_size=6, johnson_subset_size=2, embedding=emb, ambient_generators=(g2, g1)
        )
        self.assertTrue(a.certified and b.certified)
        self.assertEqual(a.reduction_identity, b.reduction_identity)

    def test_arbitrary_vertex_reindexing_with_conjugated_action_is_accepted(self):
        base = embedding(5, 2)
        reorder = (9, 0, 7, 2, 5, 1, 8, 3, 6, 4)
        emb = tuple(base[i] for i in reorder)
        gp = ground_cycle(5)
        generator = induced_vertex_permutation(emb, gp)
        out = certify_johnson_ground_relational_reduction(
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=(generator,),
        )
        self.assertTrue(out.certified)
        self.assertEqual(out.source_action_degree, 10)

    def test_rejects_incomplete_duplicate_or_malformed_embedding(self):
        emb = list(embedding(5, 2))
        bad_duplicate = list(emb)
        bad_duplicate[-1] = bad_duplicate[0]
        for bad in (emb[:-1], bad_duplicate, [*emb[:-1], (0, 0)]):
            with self.subTest(bad=bad[-1] if bad else None):
                out = certify_johnson_ground_relational_reduction(
                    johnson_ground_size=5,
                    johnson_subset_size=2,
                    embedding=bad,
                    ambient_generators=(),
                )
                self.assertFalse(out.certified)

    def test_rejects_invalid_ambient_permutation(self):
        emb = embedding(5, 2)
        bad = tuple(range(9)) + (8,)
        out = certify_johnson_ground_relational_reduction(
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=(bad,),
        )
        self.assertFalse(out.certified)
        self.assertIn("not a permutation", out.reason)

    def test_rejects_non_ground_vertex_permutation(self):
        emb = embedding(5, 2)
        bad = list(range(10))
        bad[0], bad[1] = bad[1], bad[0]
        out = certify_johnson_ground_relational_reduction(
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=(tuple(bad),),
        )
        self.assertFalse(out.certified)
        self.assertIn("star family", out.reason)

    def test_rejects_j4k2_complement_but_accepts_ground_action(self):
        emb = embedding(4, 2)
        index = {subset: i for i, subset in enumerate(emb)}
        complement = tuple(index[tuple(sorted(set(range(4)) - set(subset)))] for subset in emb)
        rejected = certify_johnson_ground_relational_reduction(
            johnson_ground_size=4,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=(complement,),
        )
        self.assertFalse(rejected.certified)
        self.assertIn("complement", rejected.reason)
        ground = induced_vertex_permutation(emb, ground_transposition(4, 0, 1))
        accepted = certify_johnson_ground_relational_reduction(
            johnson_ground_size=4,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=(ground,),
        )
        self.assertTrue(accepted.certified)

    def test_requires_strict_johnson_parameters(self):
        emb = embedding(4, 1)
        out = certify_johnson_ground_relational_reduction(
            johnson_ground_size=4,
            johnson_subset_size=1,
            embedding=emb,
            ambient_generators=(),
        )
        self.assertFalse(out.certified)
        self.assertIn("2 <= k", out.reason)
        bool_out = certify_johnson_ground_relational_reduction(
            johnson_ground_size=True,
            johnson_subset_size=2,
            embedding=(),
            ambient_generators=(),
        )
        self.assertFalse(bool_out.certified)
        self.assertIn("strict integer", bool_out.reason)

    def test_empty_generator_family_is_exact_trivial_ambient_group(self):
        emb = embedding(5, 2)
        out = certify_johnson_ground_relational_reduction(
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=(),
        )
        self.assertTrue(out.certified)
        self.assertEqual(out.induced_ground_generators, ())

    def test_replay_rejects_tampering(self):
        emb = embedding(5, 2)
        gen = induced_vertex_permutation(emb, ground_cycle(5))
        out = certify_johnson_ground_relational_reduction(
            johnson_ground_size=5,
            johnson_subset_size=2,
            embedding=emb,
            ambient_generators=(gen,),
        )
        tampered = replace(out, reduction_identity="sha256:" + "0" * 64)
        self.assertFalse(
            replay_johnson_ground_relational_reduction(
                tampered,
                johnson_ground_size=5,
                johnson_subset_size=2,
                embedding=emb,
                ambient_generators=(gen,),
            )
        )


if __name__ == "__main__":
    unittest.main()
