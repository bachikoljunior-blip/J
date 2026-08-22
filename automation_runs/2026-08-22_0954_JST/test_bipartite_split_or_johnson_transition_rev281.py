import unittest

from bipartite_split_or_johnson_transition_v1 import (
    certify_explicit_johnson_embedding,
    certify_small_part_reduction,
)


class CorrectedSOJTransitionTests(unittest.TestCase):
    def test_accepts_certified_constant_factor_small_part_reduction(self):
        cert = certify_small_part_reduction(
            theorem_input_gate=True,
            small_size_before=12,
            small_size_after=8,
            alpha=0.75,
            canonical=True,
            exact=True,
            multiplicative_cost=18.0,
            max_multiplicative_cost=32.0,
        )
        self.assertTrue(cert.progress_certified)
        self.assertEqual(cert.status, "certified_corrected_soj_small_part_reduction")

    def test_rejects_phase_like_reduction_without_strict_factor_progress(self):
        cert = certify_small_part_reduction(
            theorem_input_gate=True,
            small_size_before=12,
            small_size_after=9,
            alpha=0.75,
            canonical=True,
            exact=True,
            multiplicative_cost=1.0,
            max_multiplicative_cost=2.0,
        )
        self.assertFalse(cert.progress_certified)
        self.assertIn("constant-factor", cert.reason)

    def test_rejects_transition_when_theorem_input_gate_is_missing(self):
        cert = certify_small_part_reduction(
            theorem_input_gate=False,
            small_size_before=12,
            small_size_after=2,
            alpha=0.75,
            canonical=True,
            exact=True,
            multiplicative_cost=1.0,
            max_multiplicative_cost=2.0,
        )
        self.assertFalse(cert.progress_certified)
        self.assertIn("input gate", cert.reason)

    def test_rejects_fractional_small_sizes_instead_of_truncating(self):
        cert = certify_small_part_reduction(
            theorem_input_gate=True,
            small_size_before=12.9,
            small_size_after=2,
            alpha=0.75,
            canonical=True,
            exact=True,
            multiplicative_cost=1.0,
            max_multiplicative_cost=2.0,
        )
        self.assertFalse(cert.progress_certified)
        self.assertIn("must be an integer", cert.reason)
        self.assertIsNone(cert.small_size_before)

    def test_rejects_nonnumeric_cost_fail_closed(self):
        cert = certify_small_part_reduction(
            theorem_input_gate=True,
            small_size_before=12,
            small_size_after=2,
            alpha=0.75,
            canonical=True,
            exact=True,
            multiplicative_cost="1.0",
            max_multiplicative_cost=2.0,
        )
        self.assertFalse(cert.progress_certified)
        self.assertIn("real number", cert.reason)

    def test_accepts_explicit_johnson_relation_embedding(self):
        embedding = ({0, 1}, {0, 2}, {1, 2}, {2, 3})
        distances = {}
        for i in range(len(embedding)):
            for j in range(i + 1, len(embedding)):
                distances[(i, j)] = 2 - len(embedding[i] & embedding[j])
        cert = certify_explicit_johnson_embedding(
            theorem_input_gate=True,
            embedding=embedding,
            pair_relation_distance=distances,
            johnson_ground_size=5,
            johnson_subset_size=2,
            canonical=True,
            exact=True,
            multiplicative_cost=12.0,
            max_multiplicative_cost=16.0,
        )
        self.assertTrue(cert.progress_certified)
        self.assertEqual(cert.status, "certified_corrected_soj_explicit_johnson_embedding")

    def test_rejects_johnson_label_with_incorrect_relation(self):
        embedding = ({0, 1}, {0, 2}, {1, 2})
        distances = {(0, 1): 1, (0, 2): 1, (1, 2): 2}
        cert = certify_explicit_johnson_embedding(
            theorem_input_gate=True,
            embedding=embedding,
            pair_relation_distance=distances,
            johnson_ground_size=5,
            johnson_subset_size=2,
            canonical=True,
            exact=True,
            multiplicative_cost=1.0,
            max_multiplicative_cost=4.0,
        )
        self.assertFalse(cert.progress_certified)
        self.assertIn("intersection relation", cert.reason)

    def test_rejects_noncanonical_or_overbudget_johnson_transition(self):
        embedding = ({0, 1}, {0, 2})
        distances = {(0, 1): 1}
        cert = certify_explicit_johnson_embedding(
            theorem_input_gate=True,
            embedding=embedding,
            pair_relation_distance=distances,
            johnson_ground_size=5,
            johnson_subset_size=2,
            canonical=False,
            exact=True,
            multiplicative_cost=9.0,
            max_multiplicative_cost=4.0,
        )
        self.assertFalse(cert.progress_certified)
        self.assertIn("canonical", cert.reason)

    def test_rejects_fractional_embedding_coordinates_instead_of_coercing(self):
        embedding = ({0.9, 1.9}, {0.9, 2.9})
        distances = {(0, 1): 1}
        cert = certify_explicit_johnson_embedding(
            theorem_input_gate=True,
            embedding=embedding,
            pair_relation_distance=distances,
            johnson_ground_size=5,
            johnson_subset_size=2,
            canonical=True,
            exact=True,
            multiplicative_cost=1.0,
            max_multiplicative_cost=4.0,
        )
        self.assertFalse(cert.progress_certified)
        self.assertIn("coordinates must be integers", cert.reason)

    def test_rejects_fractional_pair_relation_distance_instead_of_coercing(self):
        embedding = ({0, 1}, {0, 2})
        distances = {(0, 1): 1.9}
        cert = certify_explicit_johnson_embedding(
            theorem_input_gate=True,
            embedding=embedding,
            pair_relation_distance=distances,
            johnson_ground_size=5,
            johnson_subset_size=2,
            canonical=True,
            exact=True,
            multiplicative_cost=1.0,
            max_multiplicative_cost=4.0,
        )
        self.assertFalse(cert.progress_certified)
        self.assertIn("intersection relation", cert.reason)


if __name__ == "__main__":
    unittest.main()
