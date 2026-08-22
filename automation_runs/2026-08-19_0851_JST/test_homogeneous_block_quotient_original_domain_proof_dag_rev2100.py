from dataclasses import replace
from types import SimpleNamespace
import unittest

from homogeneous_block_action_provenance_v1 import certify_group_block_action_equivariance
from homogeneous_block_relation_provenance_v1 import build_structure, certify_homogeneous_block_transport
from homogeneous_block_quotient_original_domain_proof_dag_rev2100 import (
    REV1800_STATUS_EXACT,
    STATUS_EXACT,
    STATUS_FAIL,
    homogeneous_block_quotient_original_domain_proof_dag_consumer,
)

DIGEST = "sha256:" + "a" * 64


def fake_rev1800(
    provenance_digest,
    *,
    status=REV1800_STATUS_EXACT,
    representative=(0, 1),
    generators=(),
    target_order=1,
    certified=True,
):
    snapshot = SimpleNamespace(
        status=status,
        exact=True,
        complete=True,
        block_count=len(representative) if representative is not None else 2,
        target_stabilizer_order=target_order,
        representative=representative,
        target_stabilizer_generators=tuple(generators),
        provenance_digest=provenance_digest,
        factorization_digest=DIGEST,
    )
    return SimpleNamespace(certified=certified, snapshot=snapshot)


def two_block_fixture(*, uniform=False):
    source = build_structure(4, unary={} if uniform else {"red": [0, 1]})
    target = build_structure(4, unary={} if uniform else {"red": [0, 1]})
    blocks = ((0, 1), (2, 3))
    relation = certify_homogeneous_block_transport(source, target, blocks, blocks, (0, 1))
    assert relation.exact and relation.certificate is not None
    generators = (
        (1, 0, 2, 3),
        (0, 1, 3, 2),
        (2, 3, 0, 1),
    )
    provenance = certify_group_block_action_equivariance(
        blocks,
        blocks,
        (0, 1),
        generators,
        generators,
    )
    assert provenance.exact
    return source, target, relation.certificate, provenance


class Rev2100OriginalDomainProofDAGTests(unittest.TestCase):
    def test_exact_nonempty_quotient_relation_coset_lifts_to_complete_parent_coset(self):
        source, target, relation, provenance = two_block_fixture()
        result = homogeneous_block_quotient_original_domain_proof_dag_consumer(
            provenance,
            source,
            target,
            relation,
            fake_rev1800(provenance.certificate_digest),
            root_n=4,
            max_quotient_enumeration=16,
        )
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertTrue(result.certified)
        self.assertTrue(result.parent_semantic_exact)
        self.assertTrue(result.quotient_semantic_complete)
        self.assertEqual(result.quotient_relation_isomorphisms_checked, 1)
        self.assertIsNotNone(result.coset)
        self.assertEqual(result.coset.subgroup.order, 4)
        self.assertEqual(result.coset.representative, (0, 1, 2, 3))

    def test_rev1800_feature_coset_strictly_smaller_than_relation_si_fails_closed(self):
        source, target, relation, provenance = two_block_fixture(uniform=True)
        result = homogeneous_block_quotient_original_domain_proof_dag_consumer(
            provenance,
            source,
            target,
            relation,
            fake_rev1800(provenance.certificate_digest),
            root_n=4,
            max_quotient_enumeration=16,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("complete quotient relation-isomorphism set", result.reason)

    def test_exact_empty_feature_result_does_not_promote_when_relation_transport_exists(self):
        source, target, relation, provenance = two_block_fixture()
        empty = fake_rev1800(
            provenance.certificate_digest,
            status="exact_empty_homogeneous_block_quotient_string_isomorphism",
            representative=None,
            target_order=0,
        )
        result = homogeneous_block_quotient_original_domain_proof_dag_consumer(
            provenance,
            source,
            target,
            relation,
            empty,
            root_n=4,
            max_quotient_enumeration=16,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertFalse(result.parent_semantic_exact)

    def test_relation_certificate_tampering_fails_closed_before_lift(self):
        source, target, relation, provenance = two_block_fixture()
        tampered = replace(relation, point_map=(1, 0, 2, 3))
        result = homogeneous_block_quotient_original_domain_proof_dag_consumer(
            provenance,
            source,
            target,
            tampered,
            fake_rev1800(provenance.certificate_digest),
            root_n=4,
            max_quotient_enumeration=16,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("relation provenance", result.reason)

    def test_rev1800_provenance_digest_drift_fails_closed(self):
        source, target, relation, provenance = two_block_fixture()
        result = homogeneous_block_quotient_original_domain_proof_dag_consumer(
            provenance,
            source,
            target,
            relation,
            fake_rev1800("sha256:" + "b" * 64),
            root_n=4,
            max_quotient_enumeration=16,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("digest", result.reason)

    def test_nonliteral_rev1800_certified_flag_is_rejected(self):
        source, target, relation, provenance = two_block_fixture()
        result = homogeneous_block_quotient_original_domain_proof_dag_consumer(
            provenance,
            source,
            target,
            relation,
            fake_rev1800(provenance.certificate_digest, certified=1),
            root_n=4,
            max_quotient_enumeration=16,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("certified=True", result.reason)

    def test_explicit_quotient_enumeration_cap_fails_closed(self):
        source, target, relation, provenance = two_block_fixture()
        result = homogeneous_block_quotient_original_domain_proof_dag_consumer(
            provenance,
            source,
            target,
            relation,
            fake_rev1800(provenance.certificate_digest),
            root_n=4,
            max_quotient_enumeration=1,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("exceeds max_quotient_enumeration", result.reason)

    def test_rev273_point_lift_must_conjugate_source_group_onto_target_group(self):
        source = build_structure(3)
        target = build_structure(3)
        blocks = ((0, 1, 2),)
        relation_result = certify_homogeneous_block_transport(source, target, blocks, blocks, (0,))
        self.assertTrue(relation_result.exact)
        provenance = certify_group_block_action_equivariance(
            blocks,
            blocks,
            (0,),
            ((1, 2, 0),),
            ((1, 0, 2),),
        )
        self.assertTrue(provenance.exact)
        snapshot = SimpleNamespace(
            status=REV1800_STATUS_EXACT,
            exact=True,
            complete=True,
            block_count=1,
            target_stabilizer_order=1,
            representative=(0,),
            target_stabilizer_generators=(),
            provenance_digest=provenance.certificate_digest,
            factorization_digest=DIGEST,
        )
        result = homogeneous_block_quotient_original_domain_proof_dag_consumer(
            provenance,
            source,
            target,
            relation_result.certificate,
            SimpleNamespace(certified=True, snapshot=snapshot),
            root_n=3,
            max_quotient_enumeration=8,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("conjugate", result.reason)

    def test_root_must_dominate_original_domain(self):
        source, target, relation, provenance = two_block_fixture()
        result = homogeneous_block_quotient_original_domain_proof_dag_consumer(
            provenance,
            source,
            target,
            relation,
            fake_rev1800(provenance.certificate_digest),
            root_n=3,
            max_quotient_enumeration=16,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("root_n", result.reason)


if __name__ == "__main__":
    unittest.main()
