from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from soj_caller_replay_envelope_v1 import (  # noqa: E402
    CallerReplayEnvelopeError,
    replay_caller_binding,
    replay_caller_replay_envelope,
    seal_caller_replay_envelope,
)


A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64


def _digest(payload):
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def binding(*, mode="small_ground_terminal", status="exact_nonempty", work=17):
    payload = {
        "schema": "corrected-soj-production-caller-binding-v1",
        "canonical": True,
        "exact": True,
        "mode": mode,
        "original_instance_identity": A,
        "transition_identity": B,
        "result_status": status,
        "result_identity": C,
        "accounted_work": work,
        "branch_certificate_identity": D,
        "branch_accounting_identity": E,
    }
    return payload | {"caller_binding_identity": _digest(payload)}


class CallerReplayEnvelopeRev500Test(unittest.TestCase):
    def test_small_ground_binding_replays_and_seals(self):
        source = binding()
        replayed = replay_caller_binding(source)
        self.assertEqual(replayed["caller_binding_identity"], source["caller_binding_identity"])
        envelope = seal_caller_replay_envelope(
            source,
            replay_verified=True,
            max_accounted_work=20,
            current_domain_size=36,
            original_root_n=100,
        )
        self.assertTrue(envelope.replay_verified)
        self.assertEqual(envelope.accounted_work, 17)
        self.assertEqual(len(envelope.envelope_identity), 64)

    def test_recursive_exact_empty_binding_is_supported(self):
        source = binding(mode="larger_ground_recursive", status="exact_empty", work=0)
        envelope = seal_caller_replay_envelope(
            source,
            replay_verified=True,
            max_accounted_work=0,
            current_domain_size=84,
            original_root_n=84,
        )
        self.assertEqual(envelope.mode, "larger_ground_recursive")
        self.assertEqual(envelope.result_status, "exact_empty")

    def test_tampered_caller_binding_identity_fails_closed(self):
        source = binding() | {"caller_binding_identity": "0" * 64}
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "does not match"):
            replay_caller_binding(source)

    def test_binding_field_drift_fails_identity_replay(self):
        source = binding()
        source["accounted_work"] = 18
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "does not match"):
            replay_caller_binding(source)

    def test_truthy_non_bool_replay_gate_is_rejected(self):
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "literal true"):
            seal_caller_replay_envelope(
                binding(),
                replay_verified=1,
                max_accounted_work=20,
                current_domain_size=36,
                original_root_n=100,
            )

    def test_bool_work_cap_is_rejected(self):
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "nonnegative integer"):
            seal_caller_replay_envelope(
                binding(),
                replay_verified=True,
                max_accounted_work=True,
                current_domain_size=36,
                original_root_n=100,
            )

    def test_accounted_work_over_cap_is_rejected(self):
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "exceeds"):
            seal_caller_replay_envelope(
                binding(work=21),
                replay_verified=True,
                max_accounted_work=20,
                current_domain_size=36,
                original_root_n=100,
            )

    def test_current_domain_cannot_exceed_original_root(self):
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "must not exceed"):
            seal_caller_replay_envelope(
                binding(),
                replay_verified=True,
                max_accounted_work=20,
                current_domain_size=101,
                original_root_n=100,
            )

    def test_invalid_mode_is_rejected_before_digest_use(self):
        source = binding()
        source["mode"] = "other"
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "binding.mode"):
            replay_caller_binding(source)

    def test_invalid_result_status_is_rejected(self):
        source = binding()
        source["result_status"] = "undetermined"
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "binding.result_status"):
            replay_caller_binding(source)

    def test_prefixed_sha_is_rejected(self):
        source = binding()
        source["transition_identity"] = "sha256:" + B
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "lowercase 64-hex"):
            replay_caller_binding(source)

    def test_negative_accounted_work_is_rejected(self):
        source = binding(work=-1)
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "nonnegative integer"):
            replay_caller_binding(source)

    def test_envelope_replays_exactly(self):
        source = binding()
        envelope = seal_caller_replay_envelope(
            source,
            replay_verified=True,
            max_accounted_work=30,
            current_domain_size=50,
            original_root_n=100,
        )
        replayed = replay_caller_replay_envelope(envelope.as_dict(), source)
        self.assertEqual(replayed, envelope)

    def test_envelope_field_drift_is_rejected(self):
        source = binding()
        envelope = seal_caller_replay_envelope(
            source,
            replay_verified=True,
            max_accounted_work=30,
            current_domain_size=50,
            original_root_n=100,
        ).as_dict()
        envelope["current_domain_size"] = 49
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "field drift|does not replay"):
            replay_caller_replay_envelope(envelope, source)

    def test_envelope_identity_tampering_is_rejected(self):
        source = binding()
        envelope = seal_caller_replay_envelope(
            source,
            replay_verified=True,
            max_accounted_work=30,
            current_domain_size=50,
            original_root_n=100,
        ).as_dict()
        envelope["envelope_identity"] = "f" * 64
        with self.assertRaisesRegex(CallerReplayEnvelopeError, "does not replay"):
            replay_caller_replay_envelope(envelope, source)


if __name__ == "__main__":
    unittest.main()
