from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_MODES = frozenset({"small_ground_terminal", "larger_ground_recursive"})
_ALLOWED_STATUSES = frozenset({"exact_nonempty", "exact_empty"})
_SCHEMA = "corrected-soj-production-caller-binding-v1"
_ROOT_KEYS = frozenset(
    {
        "canonical",
        "exact",
        "mode",
        "transition_identity",
        "original_instance_identity",
        "result_status",
        "result_identity",
        "small_ground_terminal",
        "larger_ground_recursive",
    }
)
_SMALL_GROUND_KEYS = frozenset(
    {
        "canonical",
        "exact",
        "transition_identity",
        "original_instance_identity",
        "result_status",
        "result_identity",
        "terminal_certificate_identity",
        "terminal_accounting_identity",
        "accounting_result_identity",
        "accounted_work",
    }
)
_LARGER_GROUND_KEYS = frozenset(
    {
        "canonical",
        "exact",
        "transition_identity",
        "original_instance_identity",
        "result_status",
        "result_identity",
        "recursive_result_identity",
        "recursive_accounting_binding_identity",
        "accounting_result_identity",
        "accounted_work",
    }
)


class CallerBindingError(ValueError):
    """Raised when caller-supplied proof/accounting evidence is not exactly bindable."""


def _require_mapping(value: Any, key: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise CallerBindingError(f"{key} must be a literal JSON-object dict")
    return value


def _require_schema_keys(
    mapping: Mapping[str, Any], expected: frozenset[str], key: str
) -> None:
    keys = tuple(mapping)
    if any(type(item) is not str for item in keys):
        raise CallerBindingError(f"{key} keys must be literal JSON strings")
    actual = set(keys)
    unexpected = actual - expected
    if unexpected:
        raise CallerBindingError(
            f"{key} contains unsupported fields: "
            + ", ".join(sorted(unexpected))
        )
    missing = expected - actual
    if missing:
        raise CallerBindingError(
            f"{key} is missing required fields: "
            + ", ".join(sorted(missing))
        )


def _strict_true(mapping: Mapping[str, Any], key: str) -> None:
    value = mapping.get(key)
    if type(value) is not bool or value is not True:
        raise CallerBindingError(f"{key} must be literal true")


def _strict_string(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if type(value) is not str:
        raise CallerBindingError(f"{key} must be a literal JSON string")
    return value


def _strict_sha(mapping: Mapping[str, Any], key: str) -> str:
    value = _strict_string(mapping, key)
    if _SHA256_RE.fullmatch(value) is None:
        raise CallerBindingError(f"{key} must be a lowercase 64-hex SHA-256 identity")
    return value


def _strict_nonnegative_int(mapping: Mapping[str, Any], key: str) -> int:
    value = mapping.get(key)
    if type(value) is not int or value < 0:
        raise CallerBindingError(f"{key} must be a nonnegative integer")
    return value


def _strict_status(mapping: Mapping[str, Any], key: str = "result_status") -> str:
    value = _strict_string(mapping, key)
    if value not in _ALLOWED_STATUSES:
        raise CallerBindingError(
            f"{key} must be one of {sorted(_ALLOWED_STATUSES)}"
        )
    return value


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        serialized = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    except (TypeError, ValueError) as exc:
        raise CallerBindingError(
            "binding payload is not canonically JSON serializable"
        ) from exc
    return serialized.encode("ascii")


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def bind_production_caller(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed unless one exact corrected-SOJ caller branch is fully cross-bound.

    This function intentionally does not execute String Isomorphism, construct a
    Johnson reduction, authenticate SHA-looking identities, or prove the semantic
    truth of caller-supplied certificates. It only creates a deterministic binding
    across evidence that an upstream replay/verification layer has already accepted.
    Literal dict snapshots, complete closed schemas, literal JSON-string keys, and
    literal string values are required so Python subclasses or omitted null branch
    slots cannot create multiple accepted representations of the same binding.
    """

    root = _require_mapping(evidence, "evidence")
    _require_schema_keys(root, _ROOT_KEYS, "evidence")
    _strict_true(root, "canonical")
    _strict_true(root, "exact")

    mode = _strict_string(root, "mode")
    if mode not in _ALLOWED_MODES:
        raise CallerBindingError(f"mode must be one of {sorted(_ALLOWED_MODES)}")

    transition_identity = _strict_sha(root, "transition_identity")
    original_instance_identity = _strict_sha(root, "original_instance_identity")
    result_identity = _strict_sha(root, "result_identity")
    result_status = _strict_status(root)

    small = root.get("small_ground_terminal")
    recursive = root.get("larger_ground_recursive")
    present = [small is not None, recursive is not None]
    if sum(present) != 1:
        raise CallerBindingError("exactly one branch evidence object must be present")
    if mode == "small_ground_terminal" and small is None:
        raise CallerBindingError("mode does not match present branch evidence")
    if mode == "larger_ground_recursive" and recursive is None:
        raise CallerBindingError("mode does not match present branch evidence")

    branch_key = mode
    branch = _require_mapping(root.get(branch_key), branch_key)
    expected_branch_keys = (
        _SMALL_GROUND_KEYS
        if mode == "small_ground_terminal"
        else _LARGER_GROUND_KEYS
    )
    _require_schema_keys(branch, expected_branch_keys, branch_key)
    _strict_true(branch, "canonical")
    _strict_true(branch, "exact")

    if _strict_sha(branch, "transition_identity") != transition_identity:
        raise CallerBindingError("branch transition identity does not match caller")
    if _strict_sha(branch, "original_instance_identity") != original_instance_identity:
        raise CallerBindingError("branch original-instance identity does not match caller")
    if _strict_sha(branch, "result_identity") != result_identity:
        raise CallerBindingError("branch result identity does not match caller")
    if _strict_status(branch) != result_status:
        raise CallerBindingError("branch result status does not match caller")

    accounted_work = _strict_nonnegative_int(branch, "accounted_work")

    if mode == "small_ground_terminal":
        branch_certificate_identity = _strict_sha(
            branch, "terminal_certificate_identity"
        )
        branch_accounting_identity = _strict_sha(
            branch, "terminal_accounting_identity"
        )
        accounting_result_identity = _strict_sha(
            branch, "accounting_result_identity"
        )
        if accounting_result_identity != result_identity:
            raise CallerBindingError(
                "terminal accounting does not reference the exact caller result"
            )
    else:
        branch_certificate_identity = _strict_sha(
            branch, "recursive_result_identity"
        )
        if branch_certificate_identity != result_identity:
            raise CallerBindingError(
                "recursive result identity does not match the exact caller result"
            )
        branch_accounting_identity = _strict_sha(
            branch, "recursive_accounting_binding_identity"
        )
        accounting_result_identity = _strict_sha(
            branch, "accounting_result_identity"
        )
        if accounting_result_identity != result_identity:
            raise CallerBindingError(
                "recursive accounting does not reference the exact caller result"
            )

    payload: dict[str, Any] = {
        "schema": _SCHEMA,
        "canonical": True,
        "exact": True,
        "mode": mode,
        "original_instance_identity": original_instance_identity,
        "transition_identity": transition_identity,
        "result_status": result_status,
        "result_identity": result_identity,
        "accounted_work": accounted_work,
        "branch_certificate_identity": branch_certificate_identity,
        "branch_accounting_identity": branch_accounting_identity,
    }
    payload["caller_binding_identity"] = _digest(payload)
    return payload
