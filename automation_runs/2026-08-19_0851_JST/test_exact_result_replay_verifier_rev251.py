from __future__ import annotations

from itertools import permutations
from pathlib import Path
import importlib.util
import sys
import unittest


MODULE_PATH = Path(__file__).with_name("exact_result_replay_verifier_v1.py")
SPEC = importlib.util.spec_from_file_location("exact_result_replay_verifier_v1", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


def symmetric_group(degree: int) -> tuple[tuple[int, ...], ...]:
    return tuple(permutations(range(degree)))


def exact_matches(source, target, group):
    return tuple(
        permutation
        for permutation in group
        if all(source[index] == target[permutation[index]] for index in range(len(source)))
    )


class ExactResultReplayVerifierTests(unittest.TestCase):
    def test_exact_nonempty_result_and_coset_are_verified(self) -> None:
        group = symmetric_group(3)
        source = ("red", "blue", "blue")
        target = ("blue", "red", "blue")
        matches = exact_matches(source, target, group)
        certificate = verifier.build_certificate(
            source=source,
            target=target,
            candidate_group=group,
            claimed_matches=matches,
            universe_label="S3 explicit enumeration",
        )

        result = verifier.verify_exact_result_replay(certificate)

        self.assertTrue(result.accepted)
        self.assertEqual(result.status, verifier.ReplayStatus.VERIFIED_EXACT)
        self.assertEqual(result.replayed_match_count, 2)
        self.assertEqual(result.target_stabilizer_size, 2)
        self.assertEqual(result.group_compositions, 36)

    def test_exact_empty_result_is_verified(self) -> None:
        group = symmetric_group(3)
        certificate = verifier.build_certificate(
            source=("a", "a", "b"),
            target=("a", "b", "b"),
            candidate_group=group,
            claimed_matches=(),
            universe_label="S3 color multiplicity mismatch",
        )

        result = verifier.verify_exact_result_replay(certificate)

        self.assertTrue(result.accepted)
        self.assertEqual(result.replayed_match_count, 0)
        self.assertEqual(result.target_stabilizer_size, 2)

    def test_omitted_transporter_is_rejected(self) -> None:
        group = symmetric_group(3)
        source = ("red", "blue", "blue")
        target = ("blue", "red", "blue")
        matches = exact_matches(source, target, group)
        certificate = verifier.build_certificate(
            source=source,
            target=target,
            candidate_group=group,
            claimed_matches=matches[:1],
            universe_label="tampered exact result",
        )

        result = verifier.verify_exact_result_replay(certificate)

        self.assertFalse(result.accepted)
        self.assertEqual(result.status, verifier.ReplayStatus.REJECTED)
        self.assertIn("differs", result.reason)
        self.assertEqual(result.replayed_match_count, 2)

    def test_non_group_universe_is_invalid(self) -> None:
        certificate = verifier.build_certificate(
            source=(0, 1, 2),
            target=(0, 1, 2),
            candidate_group=((0, 1, 2), (1, 0, 2), (0, 2, 1)),
            claimed_matches=((0, 1, 2),),
            universe_label="not closed",
        )

        result = verifier.verify_exact_result_replay(certificate)

        self.assertEqual(result.status, verifier.ReplayStatus.INVALID_CERTIFICATE)
        self.assertIn("not closed", result.reason)

    def test_non_exact_solver_status_fails_closed(self) -> None:
        certificate = verifier.build_certificate(
            source=(0,),
            target=(0,),
            candidate_group=((0,),),
            claimed_matches=((0,),),
            universe_label="unknown solver result",
            solver_status="unknown",
        )

        result = verifier.verify_exact_result_replay(certificate)

        self.assertEqual(result.status, verifier.ReplayStatus.INVALID_CERTIFICATE)
        self.assertIn("not exact", result.reason)
        self.assertEqual(result.group_compositions, 0)

    def test_resource_cap_stops_before_group_replay(self) -> None:
        group = symmetric_group(4)
        certificate = verifier.build_certificate(
            source=(0, 1, 2, 3),
            target=(0, 1, 2, 3),
            candidate_group=group,
            claimed_matches=((0, 1, 2, 3),),
            universe_label="S4 cap test",
        )
        caps = verifier.ReplayCaps(max_group_compositions=100)

        result = verifier.verify_exact_result_replay(certificate, caps=caps)

        self.assertEqual(result.status, verifier.ReplayStatus.UNKNOWN_RESOURCE_CAP)
        self.assertEqual(result.group_compositions, 0)
        self.assertEqual(result.action_point_checks, 0)

    def test_digest_detects_tampering(self) -> None:
        group = symmetric_group(2)
        certificate = verifier.build_certificate(
            source=("x", "y"),
            target=("x", "y"),
            candidate_group=group,
            claimed_matches=((0, 1),),
            universe_label="S2 digest",
        )
        digest = verifier.certificate_digest(certificate)
        accepted = verifier.verify_exact_result_replay(
            certificate, expected_sha256=digest
        )
        tampered = verifier.build_certificate(
            source=("x", "y"),
            target=("y", "x"),
            candidate_group=group,
            claimed_matches=((1, 0),),
            universe_label="S2 digest",
        )
        rejected = verifier.verify_exact_result_replay(
            tampered, expected_sha256=digest
        )

        self.assertTrue(accepted.accepted)
        self.assertEqual(rejected.status, verifier.ReplayStatus.REJECTED)
        self.assertIn("digest mismatch", rejected.reason)

    def test_builder_snapshots_mutable_colors(self) -> None:
        source_color = {"tags": ["a", "b"]}
        target_color = {"tags": ["a", "b"]}
        certificate = verifier.build_certificate(
            source=(source_color,),
            target=(target_color,),
            candidate_group=((0,),),
            claimed_matches=((0,),),
            universe_label="mutable snapshot",
        )
        digest = verifier.certificate_digest(certificate)
        source_color["tags"].append("mutated")
        target_color["tags"].clear()

        result = verifier.verify_exact_result_replay(
            certificate, expected_sha256=digest
        )

        self.assertTrue(result.accepted)

    def test_candidate_order_has_stable_digest(self) -> None:
        group = symmetric_group(3)
        kwargs = dict(
            source=(0, 1, 1),
            target=(1, 0, 1),
            claimed_matches=exact_matches((0, 1, 1), (1, 0, 1), group),
            universe_label="stable enumeration",
        )
        forward = verifier.build_certificate(candidate_group=group, **kwargs)
        reverse = verifier.build_certificate(candidate_group=reversed(group), **kwargs)

        self.assertEqual(
            verifier.certificate_digest(forward),
            verifier.certificate_digest(reverse),
        )

    def test_duplicate_candidate_is_not_silently_repaired(self) -> None:
        certificate = verifier.build_certificate(
            source=(0,),
            target=(0,),
            candidate_group=((0,), (0,)),
            claimed_matches=((0,),),
            universe_label="duplicate group entry",
        )

        result = verifier.verify_exact_result_replay(certificate)

        self.assertEqual(result.status, verifier.ReplayStatus.INVALID_CERTIFICATE)
        self.assertIn("duplicates", result.reason)

    def test_manually_malformed_unhashable_permutation_fails_closed(self) -> None:
        certificate = verifier.ExactResultReplayCertificate(
            schema_version=1,
            action_convention="source_i_equals_target_p_i",
            solver_status="exact",
            universe_label="malformed direct payload",
            source=(("int", "0"),),
            target=(("int", "0"),),
            candidate_group=([0],),  # type: ignore[arg-type]
            claimed_matches=(),
        )

        result = verifier.verify_exact_result_replay(certificate)

        self.assertEqual(result.status, verifier.ReplayStatus.INVALID_CERTIFICATE)
        self.assertIn("non-permutation", result.reason)


if __name__ == "__main__":
    unittest.main()
