from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


_BINDING_SCHEMA = "corrected-soj-production-caller-binding-v1"
_ENVELOPE_SCHEMA = "corrected-soj-production-caller-replay-envelope-v1"
_ALLOWED_MODES = frozenset({"small_ground_terminal", "larger_ground_recursive"})
_ALLOWED_STATUSES = frozenset({"exact_nonempty", "exact_empty"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CallerReplayEnvelopeError(ValueError):
    """Raised when a caller-binding snapshot is unsafe to replay or account."""


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CallerReplayEnvelopeError(f"{field} must be a mapping")
    return value


def _literal_true(value: Any, field: str) -> None:
    if type(value) is not bool or value is not True:
        raise CallerReplayEnvelopeError(f"{field} must be literal true")


def _strict_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CallerReplayEnvelopeError(
            f"{field} must be a lowercase 64-hex SHA-256 identity"
        )
    return value


def _strict_nonnegative_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise CallerReplayEnvelopeError(f"{field} must be a nonnegative integer")
    return value


def _strict_positive_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 1:
        raise CallerReplayEnvelopeError(f"{field} must be a positive integer")
    return value


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise CallerReplayEnvelopeError(
            "replay payload must be deterministic ASCII JSON without non-finite values"
        ) from exc


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _binding_payload(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild exactly the public rev400 caller-binding digest payload.

    This module intentionally does not import rev400 branch-only code.  It consumes
    only the published field contract and independently recomputes the digest.
    """

    if binding.get("schema") != _BINDING_SCHEMA:
        raise CallerReplayEnvelopeError("binding schema is not the rev400 public contract")
    _literal_true(binding.get("canonical"), "binding.canonical")
    _literal_true(binding.get("exact"), "binding.exact")

    mode = binding.get("mode")
    if not isinstance(mode, str) or mode not in _ALLOWED_MODES:
        raise CallerReplayEnvelopeError(
            f"binding.mode must be one of {sorted(_ALLOWED_MODES)}"
        )

    result_status = binding.get("result_status")
    if not isinstance(result_status, str) or result_status not in _ALLOWED_STATUSES:
        raise CallerReplayEnvelopeError(
            f"binding.result_status must be one of {sorted(_ALLOWED_STATUSES)}"
        )

    payload = {
        "schema": _BINDING_SCHEMA,
        "canonical": True,
        "exact": True,
        "mode": mode,
        "original_instance_identity": _strict_sha(
            binding.get("original_instance_identity"),
            "binding.original_instance_identity",
        ),
        "transition_identity": _strict_sha(
            binding.get("transition_identity"), "binding.transition_identity"
        ),
        "result_status": result_status,
        "result_identity": _strict_sha(
            binding.get("result_identity"), "binding.result_identity"
        ),
        "accounted_work": _strict_nonnegative_int(
            binding.get("accounted_work"), "binding.accounted_work"
        ),
        "branch_certificate_identity": _strict_sha(
            binding.get("branch_certificate_identity"),
            "binding.branch_certificate_identity",
        ),
        "branch_accounting_identity": _strict_sha(
            binding.get("branch_accounting_identity"),
            "binding.branch_accounting_identity",
        ),
    }
    return payload


def replay_caller_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Independently replay the deterministic identity of a rev400-shaped binding."""

    root = _require_mapping(binding, "binding")
    payload = _binding_payload(root)
    expected = _digest(payload)
    observed = _strict_sha(root.get("caller_binding_identity"), "caller_binding_identity")
    if observed != expected:
        raise CallerReplayEnvelopeError(
            "caller_binding_identity does not match the canonical rev400 public payload"
        )
    return payload | {"caller_binding_identity": expected}


@dataclass(frozen=True)
class CallerReplayEnvelope:
    schema: str
    caller_binding_identity: str
    mode: str
    result_status: str
    original_instance_identity: str
    transition_identity: str
    result_identity: str
    accounted_work: int
    max_accounted_work: int
    current_domain_size: int
    original_root_n: int
    replay_verified: bool
    envelope_identity: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "caller_binding_identity": self.caller_binding_identity,
            "mode": self.mode,
            "result_status": self.result_status,
            "original_instance_identity": self.original_instance_identity,
            "transition_identity": self.transition_identity,
            "result_identity": self.result_identity,
            "accounted_work": self.accounted_work,
            "max_accounted_work": self.max_accounted_work,
            "current_domain_size": self.current_domain_size,
            "original_root_n": self.original_root_n,
            "replay_verified": self.replay_verified,
            "envelope_identity": self.envelope_identity,
        }


def seal_caller_replay_envelope(
    binding: Mapping[str, Any],
    *,
    replay_verified: bool,
    max_accounted_work: int,
    current_domain_size: int,
    original_root_n: int,
) -> CallerReplayEnvelope:
    """Fail closed unless the caller binding replays and fits its caller envelope.

    `replay_verified` is an explicit post-replay gate.  It is intentionally strict:
    truthy integers or strings are not accepted.  The work cap and recurrence-domain
    measurements are integers so no float coercion or NaN/Inf ambiguity exists.
    """

    _literal_true(replay_verified, "replay_verified")
    work_cap = _strict_nonnegative_int(max_accounted_work, "max_accounted_work")
    current = _strict_positive_int(current_domain_size, "current_domain_size")
    root_n = _strict_positive_int(original_root_n, "original_root_n")
    if current > root_n:
        raise CallerReplayEnvelopeError(
            "current_domain_size must not exceed original_root_n"
        )

    replayed = replay_caller_binding(binding)
    accounted_work = replayed["accounted_work"]
    if accounted_work > work_cap:
        raise CallerReplayEnvelopeError(
            "caller binding accounted_work exceeds the predeclared replay envelope"
        )

    payload = {
        "schema": _ENVELOPE_SCHEMA,
        "caller_binding_identity": replayed["caller_binding_identity"],
        "mode": replayed["mode"],
        "result_status": replayed["result_status"],
        "original_instance_identity": replayed["original_instance_identity"],
        "transition_identity": replayed["transition_identity"],
        "result_identity": replayed["result_identity"],
        "accounted_work": accounted_work,
        "max_accounted_work": work_cap,
        "current_domain_size": current,
        "original_root_n": root_n,
        "replay_verified": True,
    }
    envelope_identity = _digest(payload)
    return CallerReplayEnvelope(**payload, envelope_identity=envelope_identity)


def replay_caller_replay_envelope(
    envelope: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> CallerReplayEnvelope:
    """Reconstruct an envelope and require byte-stable identity equality."""

    raw = _require_mapping(envelope, "envelope")
    if raw.get("schema") != _ENVELOPE_SCHEMA:
        raise CallerReplayEnvelopeError("envelope schema is not recognized")
    observed_identity = _strict_sha(raw.get("envelope_identity"), "envelope_identity")
    rebuilt = seal_caller_replay_envelope(
        binding,
        replay_verified=raw.get("replay_verified"),
        max_accounted_work=raw.get("max_accounted_work"),
        current_domain_size=raw.get("current_domain_size"),
        original_root_n=raw.get("original_root_n"),
    )

    for field in (
        "caller_binding_identity",
        "mode",
        "result_status",
        "original_instance_identity",
        "transition_identity",
        "result_identity",
        "accounted_work",
        "max_accounted_work",
        "current_domain_size",
        "original_root_n",
        "replay_verified",
    ):
        if raw.get(field) != getattr(rebuilt, field):
            raise CallerReplayEnvelopeError(f"envelope field drift: {field}")
    if observed_identity != rebuilt.envelope_identity:
        raise CallerReplayEnvelopeError("envelope_identity does not replay")
    return rebuilt


__all__ = [
    "CallerReplayEnvelope",
    "CallerReplayEnvelopeError",
    "replay_caller_binding",
    "seal_caller_replay_envelope",
    "replay_caller_replay_envelope",
]
