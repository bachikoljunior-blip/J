from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


_BINDING_SCHEMA = "corrected-soj-production-caller-binding-v1"
_ENVELOPE_SCHEMA = "corrected-soj-production-caller-replay-envelope-v1"
_PROVENANCE_SCHEMA = "corrected-soj-production-main-provenance-v1"
_REQUIREMENT_SCHEMA = "corrected-soj-main-provenance-requirement-v1"
_ALLOWED_MODES = frozenset({"small_ground_terminal", "larger_ground_recursive"})
_ALLOWED_STATUSES = frozenset({"exact_nonempty", "exact_empty"})
_REQUIRED_IDENTITY_FIELDS = frozenset(
    {
        "original_instance_identity",
        "transition_identity",
        "result_identity",
        "branch_certificate_identity",
        "branch_accounting_identity",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


class MainProvenanceError(ValueError):
    """Raised when corrected-SOJ production provenance cannot be verified exactly."""


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MainProvenanceError(f"{field} must be a mapping")
    return value


def _literal_true(value: Any, field: str) -> None:
    if type(value) is not bool or value is not True:
        raise MainProvenanceError(f"{field} must be literal true")


def _strict_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise MainProvenanceError(
            f"{field} must be a lowercase 64-hex SHA-256 identity"
        )
    return value


def _strict_git_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or _GIT_SHA1_RE.fullmatch(value) is None:
        raise MainProvenanceError(f"{field} must be a lowercase 40-hex Git commit SHA")
    return value


def _strict_nonnegative_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise MainProvenanceError(f"{field} must be a nonnegative integer")
    return value


def _strict_positive_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 1:
        raise MainProvenanceError(f"{field} must be a positive integer")
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
        raise MainProvenanceError(
            "provenance payload must be deterministic ASCII JSON without non-finite values"
        ) from exc


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _binding_payload(binding: Mapping[str, Any]) -> dict[str, Any]:
    if binding.get("schema") != _BINDING_SCHEMA:
        raise MainProvenanceError("binding schema is not the rev400 public contract")
    _literal_true(binding.get("canonical"), "binding.canonical")
    _literal_true(binding.get("exact"), "binding.exact")

    mode = binding.get("mode")
    if not isinstance(mode, str) or mode not in _ALLOWED_MODES:
        raise MainProvenanceError(
            f"binding.mode must be one of {sorted(_ALLOWED_MODES)}"
        )
    result_status = binding.get("result_status")
    if not isinstance(result_status, str) or result_status not in _ALLOWED_STATUSES:
        raise MainProvenanceError(
            f"binding.result_status must be one of {sorted(_ALLOWED_STATUSES)}"
        )

    return {
        "schema": _BINDING_SCHEMA,
        "canonical": True,
        "exact": True,
        "mode": mode,
        "original_instance_identity": _strict_sha256(
            binding.get("original_instance_identity"),
            "binding.original_instance_identity",
        ),
        "transition_identity": _strict_sha256(
            binding.get("transition_identity"), "binding.transition_identity"
        ),
        "result_status": result_status,
        "result_identity": _strict_sha256(
            binding.get("result_identity"), "binding.result_identity"
        ),
        "accounted_work": _strict_nonnegative_int(
            binding.get("accounted_work"), "binding.accounted_work"
        ),
        "branch_certificate_identity": _strict_sha256(
            binding.get("branch_certificate_identity"),
            "binding.branch_certificate_identity",
        ),
        "branch_accounting_identity": _strict_sha256(
            binding.get("branch_accounting_identity"),
            "binding.branch_accounting_identity",
        ),
    }


def replay_public_caller_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    root = _require_mapping(binding, "binding")
    payload = _binding_payload(root)
    expected = _digest(payload)
    observed = _strict_sha256(
        root.get("caller_binding_identity"), "binding.caller_binding_identity"
    )
    if observed != expected:
        raise MainProvenanceError(
            "caller_binding_identity does not match the canonical rev400 public payload"
        )
    return payload | {"caller_binding_identity": expected}


def seal_public_replay_envelope(
    binding: Mapping[str, Any],
    *,
    replay_verified: bool,
    max_accounted_work: int,
    current_domain_size: int,
    original_root_n: int,
) -> dict[str, Any]:
    _literal_true(replay_verified, "replay_verified")
    work_cap = _strict_nonnegative_int(max_accounted_work, "max_accounted_work")
    current = _strict_positive_int(current_domain_size, "current_domain_size")
    root_n = _strict_positive_int(original_root_n, "original_root_n")
    if current > root_n:
        raise MainProvenanceError(
            "current_domain_size must not exceed original_root_n"
        )

    replayed = replay_public_caller_binding(binding)
    accounted_work = replayed["accounted_work"]
    if accounted_work > work_cap:
        raise MainProvenanceError(
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
    return payload | {"envelope_identity": _digest(payload)}


def replay_public_replay_envelope(
    envelope: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    raw = _require_mapping(envelope, "envelope")
    if raw.get("schema") != _ENVELOPE_SCHEMA:
        raise MainProvenanceError("envelope schema is not the rev500 public contract")
    observed_identity = _strict_sha256(
        raw.get("envelope_identity"), "envelope.envelope_identity"
    )
    rebuilt = seal_public_replay_envelope(
        binding,
        replay_verified=raw.get("replay_verified"),
        max_accounted_work=raw.get("max_accounted_work"),
        current_domain_size=raw.get("current_domain_size"),
        original_root_n=raw.get("original_root_n"),
    )
    for field, expected in rebuilt.items():
        if field == "envelope_identity":
            continue
        if raw.get(field) != expected:
            raise MainProvenanceError(f"envelope field drift: {field}")
    if observed_identity != rebuilt["envelope_identity"]:
        raise MainProvenanceError("envelope_identity does not replay")
    return rebuilt


def _strict_repo_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise MainProvenanceError(f"{field} must be a nonempty repository-relative path")
    if "\x00" in value or "\n" in value or "\r" in value or "\\" in value or ":" in value:
        raise MainProvenanceError(f"{field} contains an unsafe path character")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or parsed.as_posix() != value:
        raise MainProvenanceError(f"{field} must be canonical POSIX relative syntax")
    if any(part in {"", ".", ".."} for part in parsed.parts):
        raise MainProvenanceError(f"{field} must not contain dot traversal")
    return value


def _run_git(
    repository_root: str | Path,
    *args: str,
    allow_status_one: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    root = Path(repository_root)
    if not root.exists() or not root.is_dir():
        raise MainProvenanceError("repository_root must be an existing directory")
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise MainProvenanceError("git provenance check could not execute") from exc
    if completed.returncode != 0 and not (
        allow_status_one and completed.returncode == 1
    ):
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise MainProvenanceError(
            f"git provenance check failed ({' '.join(args)}): {detail or completed.returncode}"
        )
    return completed


def _resolve_commit(repository_root: str | Path, ref: Any, field: str) -> str:
    if not isinstance(ref, str) or not ref or ref.startswith("-"):
        raise MainProvenanceError(f"{field} must be a non-option git ref")
    if any(ch.isspace() for ch in ref) or "\x00" in ref:
        raise MainProvenanceError(f"{field} must not contain whitespace or NUL")
    completed = _run_git(
        repository_root, "rev-parse", "--verify", f"{ref}^{{commit}}"
    )
    resolved = completed.stdout.decode("ascii", errors="strict").strip()
    return _strict_git_sha(resolved, field)


def _commit_is_ancestor(
    repository_root: str | Path, ancestor: str, descendant: str
) -> bool:
    completed = _run_git(
        repository_root,
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
        allow_status_one=True,
    )
    return completed.returncode == 0


def _show_blob(
    repository_root: str | Path, commit_sha: str, repository_path: str
) -> bytes:
    completed = _run_git(
        repository_root, "show", f"{commit_sha}:{repository_path}"
    )
    return completed.stdout


def _decode_json_mapping(blob: bytes, field: str) -> Mapping[str, Any]:
    try:
        text = blob.decode("utf-8")
        parsed = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MainProvenanceError(f"{field} must be UTF-8 JSON") from exc
    return _require_mapping(parsed, field)


def _normalize_requirement(
    field: str, requirement: Mapping[str, Any]
) -> dict[str, Any]:
    raw = _require_mapping(requirement, f"requirements.{field}")
    expected_keys = {
        "schema",
        "source_commit_sha",
        "source_path",
        "artifact_sha256",
        "identity_key",
    }
    if set(raw) != expected_keys:
        raise MainProvenanceError(
            f"requirements.{field} must contain exactly {sorted(expected_keys)}"
        )
    if raw.get("schema") != _REQUIREMENT_SCHEMA:
        raise MainProvenanceError(
            f"requirements.{field}.schema is not the rev600 requirement schema"
        )
    identity_key = raw.get("identity_key")
    if identity_key != field:
        raise MainProvenanceError(
            f"requirements.{field}.identity_key must equal {field!r}"
        )
    return {
        "schema": _REQUIREMENT_SCHEMA,
        "source_commit_sha": _strict_git_sha(
            raw.get("source_commit_sha"),
            f"requirements.{field}.source_commit_sha",
        ),
        "source_path": _strict_repo_path(
            raw.get("source_path"), f"requirements.{field}.source_path"
        ),
        "artifact_sha256": _strict_sha256(
            raw.get("artifact_sha256"),
            f"requirements.{field}.artifact_sha256",
        ),
        "identity_key": identity_key,
    }


@dataclass(frozen=True)
class MainIntegratedProvenance:
    schema: str
    main_commit_sha: str
    caller_binding_identity: str
    envelope_identity: str
    verified_artifacts: tuple[dict[str, Any], ...]
    provenance_identity: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "main_commit_sha": self.main_commit_sha,
            "caller_binding_identity": self.caller_binding_identity,
            "envelope_identity": self.envelope_identity,
            "verified_artifacts": [dict(item) for item in self.verified_artifacts],
            "provenance_identity": self.provenance_identity,
        }


def verify_main_integrated_provenance(
    repository_root: str | Path,
    *,
    main_ref: str,
    binding: Mapping[str, Any],
    envelope: Mapping[str, Any],
    artifact_requirements: Mapping[str, Mapping[str, Any]],
) -> MainIntegratedProvenance:
    """Bind a replayed corrected-SOJ caller result to unchanged main evidence.

    This checks repository provenance only.  It does not infer mathematical truth
    from an evidence file merely because that file is main-reachable.
    """

    replayed_binding = replay_public_caller_binding(binding)
    replayed_envelope = replay_public_replay_envelope(envelope, binding)
    requirements = _require_mapping(artifact_requirements, "artifact_requirements")
    if set(requirements) != _REQUIRED_IDENTITY_FIELDS:
        missing = sorted(_REQUIRED_IDENTITY_FIELDS - set(requirements))
        extra = sorted(set(requirements) - _REQUIRED_IDENTITY_FIELDS)
        raise MainProvenanceError(
            f"artifact requirement set mismatch: missing={missing}, extra={extra}"
        )

    main_commit = _resolve_commit(repository_root, main_ref, "main_ref")
    verified: list[dict[str, Any]] = []
    for field in sorted(_REQUIRED_IDENTITY_FIELDS):
        expected_identity = replayed_binding[field]
        requirement = _normalize_requirement(field, requirements[field])
        source_commit = requirement["source_commit_sha"]
        if not _commit_is_ancestor(repository_root, source_commit, main_commit):
            raise MainProvenanceError(
                f"{field} source commit is not reachable from the resolved main ref"
            )

        source_blob = _show_blob(
            repository_root, source_commit, requirement["source_path"]
        )
        source_blob_sha = hashlib.sha256(source_blob).hexdigest()
        if source_blob_sha != requirement["artifact_sha256"]:
            raise MainProvenanceError(
                f"{field} artifact content hash does not match its requirement"
            )

        main_blob = _show_blob(
            repository_root, main_commit, requirement["source_path"]
        )
        if main_blob != source_blob:
            raise MainProvenanceError(
                f"{field} evidence path drifted after its source commit"
            )

        artifact = _decode_json_mapping(source_blob, f"{field} artifact")
        observed_identity = _strict_sha256(
            artifact.get(requirement["identity_key"]),
            f"{field} artifact.{requirement['identity_key']}",
        )
        if observed_identity != expected_identity:
            raise MainProvenanceError(
                f"{field} does not match the main-reachable evidence artifact"
            )

        verified.append(
            {
                "identity_field": field,
                "identity": expected_identity,
                "source_commit_sha": source_commit,
                "source_path": requirement["source_path"],
                "artifact_sha256": source_blob_sha,
            }
        )

    payload: dict[str, Any] = {
        "schema": _PROVENANCE_SCHEMA,
        "main_commit_sha": main_commit,
        "caller_binding_identity": replayed_binding["caller_binding_identity"],
        "envelope_identity": replayed_envelope["envelope_identity"],
        "verified_artifacts": verified,
    }
    return MainIntegratedProvenance(
        schema=_PROVENANCE_SCHEMA,
        main_commit_sha=main_commit,
        caller_binding_identity=replayed_binding["caller_binding_identity"],
        envelope_identity=replayed_envelope["envelope_identity"],
        verified_artifacts=tuple(verified),
        provenance_identity=_digest(payload),
    )


def replay_main_integrated_provenance(
    provenance: Mapping[str, Any],
    repository_root: str | Path,
    *,
    main_ref: str,
    binding: Mapping[str, Any],
    envelope: Mapping[str, Any],
    artifact_requirements: Mapping[str, Mapping[str, Any]],
) -> MainIntegratedProvenance:
    raw = _require_mapping(provenance, "provenance")
    if raw.get("schema") != _PROVENANCE_SCHEMA:
        raise MainProvenanceError("provenance schema is not recognized")
    observed_identity = _strict_sha256(
        raw.get("provenance_identity"), "provenance.provenance_identity"
    )
    rebuilt = verify_main_integrated_provenance(
        repository_root,
        main_ref=main_ref,
        binding=binding,
        envelope=envelope,
        artifact_requirements=artifact_requirements,
    )
    expected = rebuilt.as_dict()
    for field, value in expected.items():
        if field == "provenance_identity":
            continue
        if raw.get(field) != value:
            raise MainProvenanceError(f"provenance field drift: {field}")
    if observed_identity != rebuilt.provenance_identity:
        raise MainProvenanceError("provenance_identity does not replay")
    return rebuilt


__all__ = [
    "MainIntegratedProvenance",
    "MainProvenanceError",
    "replay_public_caller_binding",
    "seal_public_replay_envelope",
    "replay_public_replay_envelope",
    "verify_main_integrated_provenance",
    "replay_main_integrated_provenance",
]
