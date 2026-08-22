from dataclasses import replace
from itertools import combinations
import unittest

from permutation_group_schreier import schreier_stabilizer_chain
from primitive_johnson_proof_dag_consumer_v1 import (
    primitive_johnson_ground_proof_dag_consumer,
    validate_primitive_johnson_ground_identity,
)


def _cycle(n):
    return tuple((i + 1) % n for i in range(n))


def _induced_symmetric_action_on_pairs(v):
    vertices = list(combinations(range(v), 2))
    index = {edge: i for i, edge in enumerate(vertices)}
    swap = list(range(v))
    swap[0], swap[1] = swap[1], swap[0]
    cyc = _cycle(v)
    generators = []
    for ground in (tuple(swap), cyc):
        generators.append(
            tuple(index[tuple(sorted(ground[x] for x in edge))] for edge in vertices)
        )
    return schreier_stabilizer_chain(generators), vertices, index


def _induced_pair_perm(vertices, index, ground_perm):
    return tuple(
        index[tuple(sorted(ground_perm[x] for x in edge))]
        for edge in vertices
    )


def _relabel_target(source, p):
    inverse = [0] * len(p)
    for i, j in enumerate(p):
        inverse[j] = i
    return tuple(source[inverse[j]] for j in range(len(p)))


class _OpaqueColor:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, _OpaqueColor) and self.value == other.value

    def __repr__(self):
        return f"_OpaqueColor({self.value})"


class PrimitiveJohnsonProofDagConsumerRev264Tests(unittest.TestCase):
    def test_exact_coset_is_admitted_to_shared_proof_dag(self):
        group, vertices, index = _induced_symmetric_action_on_pairs(5)
        witness = _induced_pair_perm(vertices, index, _cycle(5))
        source = tuple(range(group.degree))
        target = _relabel_target(source, witness)

        got = primitive_johnson_ground_proof_dag_consumer(
            group,
            source,
            target,
            root_n=16,
            max_ground_degree=5,
        )

        self.assertEqual(got.status, "certified_primitive_johnson_proof_dag")
        self.assertTrue(got.proof.exact)
        self.assertIsNotNone(got.proof.coset)
        self.assertTrue(got.proof.coset.contains(witness))
        self.assertIsNotNone(got.proof.proof_identity)
        self.assertTrue(got.proof.proof_identity.replay_stable)
        self.assertTrue(got.identity_validation.certified)
        self.assertTrue(got.dag_validation.certified)
        self.assertEqual(got.dag_validation.unique_nodes, 1)
        self.assertEqual(got.dag_validation.execution_occurrences, 1)

    def test_exact_empty_terminal_is_also_admitted(self):
        group, _vertices, _index = _induced_symmetric_action_on_pairs(5)
        source = tuple(range(group.degree))
        target = tuple(range(group.degree - 1)) + (999,)

        got = primitive_johnson_ground_proof_dag_consumer(
            group,
            source,
            target,
            root_n=16,
            max_ground_degree=5,
        )

        self.assertEqual(got.status, "certified_primitive_johnson_proof_dag")
        self.assertTrue(got.proof.exact)
        self.assertIsNone(got.proof.coset)
        self.assertEqual(got.proof.status, "exact_empty_primitive_johnson_ground")
        self.assertTrue(got.identity_validation.certified)
        self.assertTrue(got.dag_validation.certified)

    def test_nonjohnson_unresolved_execution_gets_no_identity(self):
        group = schreier_stabilizer_chain([_cycle(11)])
        source = tuple(range(group.degree))

        got = primitive_johnson_ground_proof_dag_consumer(
            group,
            source,
            source,
            root_n=16,
            max_ground_degree=5,
        )

        self.assertEqual(got.status, "underlying_primitive_johnson_terminal_not_exact")
        self.assertFalse(got.proof.exact)
        self.assertIsNone(got.proof.proof_identity)
        self.assertIsNone(got.identity_validation)
        self.assertIsNone(got.dag_validation)

    def test_opaque_colors_fail_shared_replay_closed(self):
        group, vertices, index = _induced_symmetric_action_on_pairs(5)
        witness = _induced_pair_perm(vertices, index, _cycle(5))
        source = tuple(_OpaqueColor(i) for i in range(group.degree))
        target = _relabel_target(source, witness)

        got = primitive_johnson_ground_proof_dag_consumer(
            group,
            source,
            target,
            root_n=16,
            max_ground_degree=5,
        )

        self.assertEqual(got.status, "unstable_opaque_primitive_johnson_identity")
        self.assertTrue(got.proof.exact)
        self.assertIsNone(got.proof.proof_identity)
        self.assertFalse(got.identity_validation.certified)
        self.assertIsNone(got.dag_validation)

    def test_tampered_identity_is_rejected_before_dag_reuse(self):
        group, vertices, index = _induced_symmetric_action_on_pairs(5)
        witness = _induced_pair_perm(vertices, index, _cycle(5))
        source = tuple(range(group.degree))
        target = _relabel_target(source, witness)

        got = primitive_johnson_ground_proof_dag_consumer(
            group,
            source,
            target,
            root_n=16,
            max_ground_degree=5,
        )
        expected = got.proof.proof_identity
        tampered = replace(expected, root_n=expected.root_n + 1)
        tampered_proof = replace(got.proof, proof_identity=tampered)

        checked = validate_primitive_johnson_ground_identity(tampered_proof, expected)
        self.assertEqual(checked.status, "mismatched_primitive_johnson_proof_identity")
        self.assertFalse(checked.certified)


if __name__ == "__main__":
    unittest.main()
