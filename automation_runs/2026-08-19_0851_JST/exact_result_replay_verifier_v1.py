"""Fail-closed replay verification for exact finite-group SI results.

The verifier is deliberately solver-independent.  It proves exactness only
relative to an explicitly enumerated finite permutation group: every group
element is replayed, the complete match set is compared with the producer's
claim, and every non-empty result is checked against the target stabilizer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import math
from typing import Any, Iterable, Sequence, TypeAlias


Permutation: TypeAlias = tuple[int, ...]
FrozenValue: TypeAlias = tuple[Any, ...]


class CertificateBuildError(ValueError):
    """The caller supplied data that cannot be snapshotted deterministically."""


class ReplayStatus(str, Enum):
    VERIFIED_EXACT = "verified_exact"
    REJECTED = "rejected"
    INVALID_CERTIFICATE = "invalid_certificate"
    UNKNOWN_RESOURCE_CAP = "unknown_resource_cap"


@dataclass(frozen=True)
class ReplayCaps:
    max_degree: int = 64
    max_group_size: int = 2_048
    max_group_compositions: int = 1_000_000
    max_action_point_checks: int = 1_000_000
    max_certificate_bytes: int = 4_000_000

    def validate(self) -> None:
        for name, value in vars(self).items():
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True)
class ExactResultReplayCertificate:
    schema_version: int
    action_convention: str
    solver_status: str
    universe_label: str
    source: tuple[FrozenValue, ...]
    target: tuple[FrozenValue, ...]
    candidate_group: tuple[Permutation, ...]
    claimed_matches: tuple[Permutation, ...]


@dataclass(frozen=True)
class ReplayVerification:
    status: ReplayStatus
    reason: str
    certificate_sha256: str | None
    degree: int
    group_size: int
    claimed_match_count: int
    replayed_match_count: int
    target_stabilizer_size: int | None
    group_compositions: int
    action_point_checks: int

    @property
    def accepted(self) -> bool:
        return self.status is ReplayStatus.VERIFIED_EXACT


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _freeze(value: Any) -> FrozenValue:
    if value is None:
        return ("none",)
    if type(value) is bool:
        return ("bool", value)
    if type(value) is int:
        return ("int", str(value))
    if type(value) is float:
        if not math.isfinite(value):
            raise CertificateBuildError("non-finite float colors are unsupported")
        return ("float", value.hex())
    if type(value) is str:
        return ("str", value)
    if type(value) is bytes:
        return ("bytes", value.hex())
    if type(value) in (list, tuple):
        return (type(value).__name__, tuple(_freeze(item) for item in value))
    if type(value) is dict:
        items = [(_freeze(key), _freeze(item)) for key, item in value.items()]
        items.sort(key=lambda pair: _canonical_bytes(pair[0]))
        if any(left[0] == right[0] for left, right in zip(items, items[1:])):
            raise CertificateBuildError("mapping has duplicate canonical keys")
        return ("dict", tuple(items))
    kind = f"{type(value).__module__}.{type(value).__qualname__}"
    raise CertificateBuildError(f"unsupported color type {kind}")


def _permutation(raw: Iterable[int]) -> Permutation:
    try:
        result = tuple(raw)
    except TypeError as exc:
        raise CertificateBuildError("permutation must be iterable") from exc
    if any(type(value) is not int for value in result):
        raise CertificateBuildError("permutation entries must be integers")
    return result


def build_certificate(
    *,
    source: Sequence[Any],
    target: Sequence[Any],
    candidate_group: Iterable[Iterable[int]],
    claimed_matches: Iterable[Iterable[int]],
    universe_label: str,
    solver_status: str = "exact",
) -> ExactResultReplayCertificate:
    """Snapshot mutable inputs; preserve duplicates for explicit rejection."""

    if type(universe_label) is not str or not universe_label:
        raise CertificateBuildError("universe_label must be a non-empty string")
    if type(solver_status) is not str:
        raise CertificateBuildError("solver_status must be a string")
    return ExactResultReplayCertificate(
        schema_version=1,
        action_convention="source_i_equals_target_p_i",
        solver_status=solver_status,
        universe_label=universe_label,
        source=tuple(_freeze(value) for value in tuple(source)),
        target=tuple(_freeze(value) for value in tuple(target)),
        candidate_group=tuple(sorted(_permutation(p) for p in candidate_group)),
        claimed_matches=tuple(sorted(_permutation(p) for p in claimed_matches)),
    )


def _payload(certificate: ExactResultReplayCertificate) -> dict[str, Any]:
    return {
        "schema_version": certificate.schema_version,
        "action_convention": certificate.action_convention,
        "solver_status": certificate.solver_status,
        "universe_label": certificate.universe_label,
        "source": certificate.source,
        "target": certificate.target,
        "candidate_group": certificate.candidate_group,
        "claimed_matches": certificate.claimed_matches,
    }


def certificate_digest(certificate: ExactResultReplayCertificate) -> str:
    return sha256(_canonical_bytes(_payload(certificate))).hexdigest()


def _compose(left: Permutation, right: Permutation) -> Permutation:
    return tuple(left[right[index]] for index in range(len(left)))


def _valid_permutation(value: Any, degree: int) -> bool:
    return (
        type(value) is tuple
        and len(value) == degree
        and all(type(point) is int for point in value)
        and set(value) == set(range(degree))
    )


def _transports(
    source: tuple[FrozenValue, ...],
    target: tuple[FrozenValue, ...],
    permutation: Permutation,
) -> bool:
    # p maps source point i to target point p[i].
    return all(source[i] == target[permutation[i]] for i in range(len(source)))


def _outcome(
    status: ReplayStatus,
    reason: str,
    *,
    digest: str | None = None,
    degree: int = 0,
    group_size: int = 0,
    claimed: int = 0,
    replayed: int = 0,
    stabilizer: int | None = None,
    compositions: int = 0,
    checks: int = 0,
) -> ReplayVerification:
    return ReplayVerification(
        status=status,
        reason=reason,
        certificate_sha256=digest,
        degree=degree,
        group_size=group_size,
        claimed_match_count=claimed,
        replayed_match_count=replayed,
        target_stabilizer_size=stabilizer,
        group_compositions=compositions,
        action_point_checks=checks,
    )


def verify_exact_result_replay(
    certificate: ExactResultReplayCertificate,
    *,
    caps: ReplayCaps = ReplayCaps(),
    expected_sha256: str | None = None,
) -> ReplayVerification:
    """Replay one certificate and accept only a complete bounded proof."""

    invalid = ReplayStatus.INVALID_CERTIFICATE
    unknown = ReplayStatus.UNKNOWN_RESOURCE_CAP

    try:
        caps.validate()
    except ValueError as exc:
        return _outcome(invalid, f"invalid caps: {exc}")
    if not isinstance(certificate, ExactResultReplayCertificate):
        return _outcome(invalid, "payload is not an ExactResultReplayCertificate")
    if certificate.schema_version != 1:
        return _outcome(invalid, "unsupported schema_version")
    if certificate.action_convention != "source_i_equals_target_p_i":
        return _outcome(invalid, "unsupported action_convention")
    if certificate.solver_status != "exact":
        return _outcome(invalid, "solver_status is not exact")
    if type(certificate.universe_label) is not str or not certificate.universe_label:
        return _outcome(invalid, "universe_label must be a non-empty string")
    if type(certificate.source) is not tuple or type(certificate.target) is not tuple:
        return _outcome(invalid, "source and target must be immutable tuples")
    if type(certificate.candidate_group) is not tuple:
        return _outcome(invalid, "candidate_group must be an immutable tuple")
    if type(certificate.claimed_matches) is not tuple:
        return _outcome(invalid, "claimed_matches must be an immutable tuple")

    degree = len(certificate.source)
    group = certificate.candidate_group
    claimed_matches = certificate.claimed_matches
    group_size = len(group)
    claimed = len(claimed_matches)
    context = dict(degree=degree, group_size=group_size, claimed=claimed)

    if len(certificate.target) != degree:
        return _outcome(invalid, "source and target have different degrees", **context)
    if degree > caps.max_degree:
        return _outcome(unknown, "degree exceeds max_degree", **context)
    if not group:
        return _outcome(invalid, "candidate_group is empty", **context)
    if group_size > caps.max_group_size:
        return _outcome(unknown, "candidate group exceeds max_group_size", **context)

    try:
        payload_bytes = _canonical_bytes(_payload(certificate))
    except (TypeError, ValueError) as exc:
        return _outcome(
            invalid, f"certificate is not canonically serializable: {exc}", **context
        )
    if len(payload_bytes) > caps.max_certificate_bytes:
        return _outcome(unknown, "certificate exceeds max_certificate_bytes", **context)
    digest = sha256(payload_bytes).hexdigest()
    context["digest"] = digest

    if expected_sha256 is not None:
        if type(expected_sha256) is not str or len(expected_sha256) != 64:
            return _outcome(
                invalid,
                "expected_sha256 must be a 64-character hexadecimal string",
                **context,
            )
        try:
            int(expected_sha256, 16)
        except ValueError:
            return _outcome(invalid, "expected_sha256 must be hexadecimal", **context)
        if digest != expected_sha256.lower():
            return _outcome(
                ReplayStatus.REJECTED, "certificate digest mismatch", **context
            )

    if not all(_valid_permutation(p, degree) for p in group):
        return _outcome(invalid, "candidate_group contains a non-permutation", **context)
    if not all(_valid_permutation(p, degree) for p in claimed_matches):
        return _outcome(invalid, "claimed_matches contains a non-permutation", **context)
    if len(set(group)) != group_size:
        return _outcome(invalid, "candidate_group contains duplicates", **context)
    if len(set(claimed_matches)) != claimed:
        return _outcome(invalid, "claimed_matches contains duplicates", **context)

    group_set = set(group)
    if not set(claimed_matches).issubset(group_set):
        return _outcome(
            invalid, "claimed_matches is not a subset of candidate_group", **context
        )
    if tuple(range(degree)) not in group_set:
        return _outcome(
            invalid, "candidate_group does not contain the identity", **context
        )

    required_compositions = group_size * group_size
    required_checks = 2 * group_size * degree
    if required_compositions > caps.max_group_compositions:
        return _outcome(
            unknown,
            "group closure replay exceeds max_group_compositions",
            **context,
        )
    if required_checks > caps.max_action_point_checks:
        return _outcome(
            unknown, "action replay exceeds max_action_point_checks", **context
        )

    compositions = 0
    for left in group:
        for right in group:
            compositions += 1
            if _compose(left, right) not in group_set:
                return _outcome(
                    invalid,
                    "candidate_group is not closed under composition",
                    compositions=compositions,
                    **context,
                )

    replayed_matches = tuple(
        sorted(p for p in group if _transports(certificate.source, certificate.target, p))
    )
    stabilizer = tuple(
        sorted(p for p in group if _transports(certificate.target, certificate.target, p))
    )
    replay_context = dict(
        replayed=len(replayed_matches),
        stabilizer=len(stabilizer),
        compositions=compositions,
        checks=required_checks,
        **context,
    )

    if replayed_matches:
        transporter = replayed_matches[0]
        reconstructed = {_compose(h, transporter) for h in stabilizer}
        if reconstructed != set(replayed_matches):
            return _outcome(
                ReplayStatus.REJECTED,
                "replayed matches fail target-stabilizer coset reconstruction",
                **replay_context,
            )
    if tuple(sorted(claimed_matches)) != replayed_matches:
        return _outcome(
            ReplayStatus.REJECTED,
            "claimed exact match set differs from complete replay",
            **replay_context,
        )
    return _outcome(
        ReplayStatus.VERIFIED_EXACT,
        "complete finite-group replay and coset check succeeded",
        **replay_context,
    )
