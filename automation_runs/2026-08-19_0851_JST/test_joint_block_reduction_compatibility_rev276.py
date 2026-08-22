from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from homogeneous_block_action_provenance_v1 import (  # noqa: E402
    certify_group_block_action_equivariance,
)
from joint_block_reduction_compatibility_v1 import (  # noqa: E402
    STATUS_EXACT,
    certify_joint_block_reduction_compatibility,
    replay_joint_block_reduction_compatibility,
)


@dataclass(frozen=True)
class QuotientRelation:
    name: str
    arity: int
    tuples: frozenset[tuple[int, ...]]


@dataclass(frozen=True)
class QuotientStructure:
    block_count: int
    block_sizes: tuple[int, ...]
    relations: tuple[QuotientRelation, ...]


@dataclass(frozen=True)
class RelationCertificate:
    source_partition: tuple[tuple[int, ...], ...]
    target_partition: tuple[tuple[int, ...], ...]
    block_map: tuple[int, ...]
    point_map: tuple[int, ...]
    source_quotient: QuotientStructure
    target_quotient: QuotientStructure


@dataclass(frozen=True)
class RelationResult:
    exact: bool
    reason: str
    certificate: RelationCertificate | None


def _relation_result(**overrides) -> RelationResult:
    source_q = QuotientStructure(
        block_count=2,
        block_sizes=(2, 2),
        relations=(QuotientRelation("u", 1, frozenset({(0,)})),),
    )
    target_q = QuotientStructure(
        block_count=2,
        block_sizes=(2, 2),
        relations=(QuotientRelation("u", 1, frozenset({(1,)})),),
    )
    certificate = RelationCertificate(
        source_partition=((2, 3), (0, 1)),
        target_partition=((0, 1), (2, 3)),
        block_map=(1, 0),
        point_map=(0, 1, 2, 3),
        source_quotient=source_q,
        target_quotient=target_q,
    )
    values = {
        "exact": True,
        "reason": "exact_homogeneous_block_transport",
        "certificate": certificate,
    }
    values.update(overrides)
    return RelationResult(**values)


def _action_certificate():
    result = certify_group_block_action_equivariance(
        ((2, 3), (0, 1)),
        ((0, 1), (2, 3)),
        (1, 0),
        ((2, 3, 0, 1), (1, 0, 3, 2)),
        ((2, 3, 0, 1), (1, 0, 3, 2)),
    )
    if not result.exact:
        raise AssertionError(result.reason)
    return result


class JointBlockReductionCompatibilityTests(unittest.TestCase):
    def test_exact_compatible_upstream_evidence_is_bound(self):
        relation = _relation_result()
        action = _action_certificate()
        result = certify_joint_block_reduction_compatibility(relation, action)
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertEqual(result.domain_degree, 4)
        self.assertEqual(result.source_blocks, ((0, 1), (2, 3)))
        self.assertEqual(result.target_blocks, ((0, 1), (2, 3)))
        self.assertEqual(result.block_bijection, (0, 1))
        self.assertTrue(result.relation_identity_digest.startswith("sha256:"))
        self.assertEqual(result.action_certificate_digest, action.certificate_digest)
        self.assertTrue(result.joint_certificate_digest.startswith("sha256:"))

    def test_exact_certificate_replays_deterministically(self):
        relation = _relation_result()
        action = _action_certificate()
        result = certify_joint_block_reduction_compatibility(relation, action)
        self.assertTrue(
            replay_joint_block_reduction_compatibility(relation, action, result)
        )

    def test_top_level_mapping_relation_result_is_supported(self):
        relation = _relation_result()
        mapping = {
            "exact": relation.exact,
            "reason": relation.reason,
            "certificate": relation.certificate,
        }
        result = certify_joint_block_reduction_compatibility(
            mapping, _action_certificate()
        )
        self.assertTrue(result.exact)

    def test_nonexact_relation_result_fails_closed(self):
        relation = _relation_result(exact=False)
        result = certify_joint_block_reduction_compatibility(
            relation, _action_certificate()
        )
        self.assertFalse(result.exact)
        self.assertIn("relation result is not exact", result.reason)

    def test_missing_relation_certificate_fails_closed(self):
        relation = _relation_result(certificate=None)
        result = certify_joint_block_reduction_compatibility(
            relation, _action_certificate()
        )
        self.assertFalse(result.exact)
        self.assertIn("no certificate", result.reason)

    def test_source_partition_mismatch_fails_closed(self):
        relation = _relation_result()
        assert relation.certificate is not None
        bad_certificate = replace(
            relation.certificate,
            source_partition=((0, 2), (1, 3)),
        )
        result = certify_joint_block_reduction_compatibility(
            replace(relation, certificate=bad_certificate), _action_certificate()
        )
        self.assertFalse(result.exact)
        self.assertIn("source partitions differ", result.reason)

    def test_block_bijection_mismatch_fails_closed(self):
        relation = _relation_result()
        assert relation.certificate is not None
        bad_certificate = replace(relation.certificate, block_map=(0, 1))
        result = certify_joint_block_reduction_compatibility(
            replace(relation, certificate=bad_certificate), _action_certificate()
        )
        self.assertFalse(result.exact)
        self.assertIn("block bijections differ", result.reason)

    def test_point_map_must_realize_common_block_bijection(self):
        relation = _relation_result()
        assert relation.certificate is not None
        bad_certificate = replace(
            relation.certificate,
            point_map=(2, 3, 0, 1),
        )
        result = certify_joint_block_reduction_compatibility(
            replace(relation, certificate=bad_certificate), _action_certificate()
        )
        self.assertFalse(result.exact)
        self.assertIn("point_map does not realize", result.reason)

    def test_relation_quotient_dimensions_must_match_action(self):
        relation = _relation_result()
        assert relation.certificate is not None
        bad_source_q = replace(
            relation.certificate.source_quotient,
            block_sizes=(1, 3),
        )
        bad_certificate = replace(
            relation.certificate,
            source_quotient=bad_source_q,
        )
        result = certify_joint_block_reduction_compatibility(
            replace(relation, certificate=bad_certificate), _action_certificate()
        )
        self.assertFalse(result.exact)
        self.assertIn("block_sizes mismatch", result.reason)

    def test_relation_quotient_signatures_must_match(self):
        relation = _relation_result()
        assert relation.certificate is not None
        bad_target_q = replace(
            relation.certificate.target_quotient,
            relations=(QuotientRelation("different", 1, frozenset({(1,)})),),
        )
        bad_certificate = replace(
            relation.certificate,
            target_quotient=bad_target_q,
        )
        result = certify_joint_block_reduction_compatibility(
            replace(relation, certificate=bad_certificate), _action_certificate()
        )
        self.assertFalse(result.exact)
        self.assertIn("relation signatures differ", result.reason)

    def test_tampered_action_digest_fails_closed(self):
        action = replace(_action_certificate(), certificate_digest="sha256:" + "0" * 64)
        result = certify_joint_block_reduction_compatibility(
            _relation_result(), action
        )
        self.assertFalse(result.exact)
        self.assertIn("digest mismatch", result.reason)

    def test_tampered_joint_certificate_does_not_replay(self):
        relation = _relation_result()
        action = _action_certificate()
        result = certify_joint_block_reduction_compatibility(relation, action)
        tampered = replace(
            result,
            joint_certificate_digest="sha256:" + "f" * 64,
        )
        self.assertFalse(
            replay_joint_block_reduction_compatibility(
                relation, action, tampered
            )
        )


if __name__ == "__main__":
    unittest.main()
