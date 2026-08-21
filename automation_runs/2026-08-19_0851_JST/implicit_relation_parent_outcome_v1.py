from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Iterable


SCHEMA_VERSION = 1
NONEMPTY_SOURCE_REVISION = 261
EXACT_EMPTY_SOURCE_REVISION = 263
NONEMPTY_STATUS = "exact_implicit_relation_parent_coset"
EXACT_EMPTY_STATUSES = frozenset(
    {
        "exact_empty_parent_domain_size_mismatch",
        "exact_empty_parent_relation_signature_mismatch",
        "exact_empty_parent_feature_inventory_mismatch",
    }
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ParentOutcomeContractError(ValueError):
    """Raised when an upstream exact-evidence adapter is used incorrectly."""


@dataclass(frozen=True)
class ParentOutcomeTranscript:
    schema_version: int
    source_evidence_revision: int
    source_evidence_status: str
    outcome_kind: str
    exact: bool
    complete: bool
    domain_degree: int
    auxiliary_degree: int
    source_relation_digest: str
    target_relation_digest: str
    upstream_artifact_digest: str
    transcript_digest: str


@dataclass(frozen=True)
class ParentExactOutcomeContract:
    status: str
    exact: bool
    complete: bool
    outcome_kind: str
    domain_degree: int
    auxiliary_degree: int
    source_evidence_revision: int
    source_evidence_status: str
    source_relation_digest: str
    target_relation_digest: str
    upstream_artifact_digest: str
    transcript_digest: str
    reason: str


def _require_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ParentOutcomeContractError(
            f"{field} must be a lowercase sha256:<64 hex> digest"
        )
    return value


def _require_nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ParentOutcomeContractError(f"{field} must be a nonnegative integer")
    return value


def _canonical_transcript_payload(
    *,
    source_evidence_revision: int,
    source_evidence_status: str,
    outcome_kind: str,
    exact: bool,
    complete: bool,
    domain_degree: int,
    auxiliary_degree: int,
    source_relation_digest: str,
    target_relation_digest: str,
    upstream_artifact_digest: str,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_evidence_revision": source_evidence_revision,
        "source_evidence_status": source_evidence_status,
        "outcome_kind": outcome_kind,
        "exact": exact,
        "complete": complete,
        "domain_degree": domain_degree,
        "auxiliary_degree": auxiliary_degree,
        "source_relation_digest": source_relation_digest,
        "target_relation_digest": target_relation_digest,
        "upstream_artifact_digest": upstream_artifact_digest,
    }


def _digest_payload(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _build_transcript(
    *,
    source_evidence_revision: int,
    source_evidence_status: str,
    outcome_kind: str,
    exact: bool,
    complete: bool,
    domain_degree: int,
    auxiliary_degree: int,
    source_relation_digest: str,
    target_relation_digest: str,
    upstream_artifact_digest: str,
) -> ParentOutcomeTranscript:
    source_relation_digest = _require_sha256(
        source_relation_digest, "source_relation_digest"
    )
    target_relation_digest = _require_sha256(
        target_relation_digest, "target_relation_digest"
    )
    upstream_artifact_digest = _require_sha256(
        upstream_artifact_digest, "upstream_artifact_digest"
    )
    domain_degree = _require_nonnegative_int(domain_degree, "domain_degree")
    auxiliary_degree = _require_nonnegative_int(auxiliary_degree, "auxiliary_degree")
    payload = _canonical_transcript_payload(
        source_evidence_revision=source_evidence_revision,
        source_evidence_status=source_evidence_status,
        outcome_kind=outcome_kind,
        exact=exact,
        complete=complete,
        domain_degree=domain_degree,
        auxiliary_degree=auxiliary_degree,
        source_relation_digest=source_relation_digest,
        target_relation_digest=target_relation_digest,
        upstream_artifact_digest=upstream_artifact_digest,
    )
    return ParentOutcomeTranscript(
        **payload,
        transcript_digest=_digest_payload(payload),
    )


def transcript_from_nonempty_promotion(
    promotion: object,
    *,
    source_relation_digest: str,
    target_relation_digest: str,
    upstream_artifact_digest: str,
) -> ParentOutcomeTranscript:
    """Adapt an already verified rev261 nonempty promotion into a stable transcript."""
    status = getattr(promotion, "status", None)
    exact = getattr(promotion, "exact", None)
    complete = getattr(promotion, "complete", None)
    domain_degree = getattr(promotion, "domain_degree", None)
    auxiliary_degree = getattr(promotion, "auxiliary_degree", None)
    coset = getattr(promotion, "coset", None)

    if status != NONEMPTY_STATUS or exact is not True or complete is not True:
        raise ParentOutcomeContractError(
            "nonempty transcript requires the exact complete rev261 promotion status"
        )
    if coset is None:
        raise ParentOutcomeContractError(
            "exact rev261 nonempty promotion must carry a nonempty right coset"
        )

    return _build_transcript(
        source_evidence_revision=NONEMPTY_SOURCE_REVISION,
        source_evidence_status=status,
        outcome_kind="nonempty",
        exact=True,
        complete=True,
        domain_degree=domain_degree,
        auxiliary_degree=auxiliary_degree,
        source_relation_digest=source_relation_digest,
        target_relation_digest=target_relation_digest,
        upstream_artifact_digest=upstream_artifact_digest,
    )


def transcript_from_exact_empty_promotion(
    evidence: object,
    *,
    source_relation_digest: str,
    target_relation_digest: str,
    upstream_artifact_digest: str,
) -> ParentOutcomeTranscript:
    """Adapt an already verified rev263 exact-empty promotion into a stable transcript."""
    status = getattr(evidence, "status", None)
    exact = getattr(evidence, "exact", None)
    complete = getattr(evidence, "complete", None)
    domain_degree = getattr(evidence, "domain_degree", None)
    auxiliary_degree = getattr(evidence, "auxiliary_degree", None)

    if status not in EXACT_EMPTY_STATUSES or exact is not True or complete is not True:
        raise ParentOutcomeContractError(
            "exact-empty transcript requires an exact complete rev263 empty status"
        )

    transcript = _build_transcript(
        source_evidence_revision=EXACT_EMPTY_SOURCE_REVISION,
        source_evidence_status=status,
        outcome_kind="exact_empty",
        exact=True,
        complete=True,
        domain_degree=domain_degree,
        auxiliary_degree=auxiliary_degree,
        source_relation_digest=source_relation_digest,
        target_relation_digest=target_relation_digest,
        upstream_artifact_digest=upstream_artifact_digest,
    )
    if (
        status == "exact_empty_parent_feature_inventory_mismatch"
        and transcript.auxiliary_degree == 0
    ):
        raise ParentOutcomeContractError(
            "feature-inventory exact-empty evidence must identify a positive auxiliary degree"
        )
    return transcript


def _recompute_transcript_digest(transcript: ParentOutcomeTranscript) -> str:
    payload = _canonical_transcript_payload(
        source_evidence_revision=transcript.source_evidence_revision,
        source_evidence_status=transcript.source_evidence_status,
        outcome_kind=transcript.outcome_kind,
        exact=transcript.exact,
        complete=transcript.complete,
        domain_degree=transcript.domain_degree,
        auxiliary_degree=transcript.auxiliary_degree,
        source_relation_digest=transcript.source_relation_digest,
        target_relation_digest=transcript.target_relation_digest,
        upstream_artifact_digest=transcript.upstream_artifact_digest,
    )
    return _digest_payload(payload)


def _closed(
    status: str,
    *,
    reason: str,
    expected_source_relation_digest: str,
    expected_target_relation_digest: str,
    expected_domain_degree: int,
) -> ParentExactOutcomeContract:
    return ParentExactOutcomeContract(
        status=status,
        exact=False,
        complete=False,
        outcome_kind="undetermined",
        domain_degree=expected_domain_degree,
        auxiliary_degree=0,
        source_evidence_revision=0,
        source_evidence_status="",
        source_relation_digest=expected_source_relation_digest,
        target_relation_digest=expected_target_relation_digest,
        upstream_artifact_digest="",
        transcript_digest="",
        reason=reason,
    )


def normalize_parent_exact_outcome(
    transcripts: Iterable[ParentOutcomeTranscript],
    *,
    expected_source_relation_digest: str,
    expected_target_relation_digest: str,
    expected_domain_degree: int,
) -> ParentExactOutcomeContract:
    """Normalize exactly one independently verified parent outcome.

    This function is intentionally evidence-only. It does not repeat the rev261
    nonempty semantic verifier, the rev263 exact-empty verifier, image-coset
    intersection, or paired-preimage construction. It binds one accepted
    upstream transcript to the caller's exact parent relation identity and
    returns a replay-stable typed outcome.

    Missing, multiple, malformed, context-mismatched, or digest-corrupted
    transcripts all fail closed.
    """
    expected_source_relation_digest = _require_sha256(
        expected_source_relation_digest, "expected_source_relation_digest"
    )
    expected_target_relation_digest = _require_sha256(
        expected_target_relation_digest, "expected_target_relation_digest"
    )
    expected_domain_degree = _require_nonnegative_int(
        expected_domain_degree, "expected_domain_degree"
    )

    items = tuple(transcripts)
    if not items:
        return _closed(
            "fail_closed_missing_exact_parent_outcome",
            reason="no independently verified exact parent outcome transcript was supplied",
            expected_source_relation_digest=expected_source_relation_digest,
            expected_target_relation_digest=expected_target_relation_digest,
            expected_domain_degree=expected_domain_degree,
        )
    if len(items) != 1:
        return _closed(
            "fail_closed_contradictory_parent_outcomes",
            reason="exactly one parent outcome transcript is required; multiple exact claims are not reconciled here",
            expected_source_relation_digest=expected_source_relation_digest,
            expected_target_relation_digest=expected_target_relation_digest,
            expected_domain_degree=expected_domain_degree,
        )

    transcript = items[0]
    if not isinstance(transcript, ParentOutcomeTranscript):
        return _closed(
            "fail_closed_invalid_parent_outcome_transcript_type",
            reason="parent outcome transcript has the wrong runtime type",
            expected_source_relation_digest=expected_source_relation_digest,
            expected_target_relation_digest=expected_target_relation_digest,
            expected_domain_degree=expected_domain_degree,
        )
    if transcript.schema_version != SCHEMA_VERSION:
        return _closed(
            "fail_closed_parent_outcome_schema_version",
            reason="parent outcome transcript schema version is not recognized",
            expected_source_relation_digest=expected_source_relation_digest,
            expected_target_relation_digest=expected_target_relation_digest,
            expected_domain_degree=expected_domain_degree,
        )
    try:
        _require_sha256(transcript.source_relation_digest, "source_relation_digest")
        _require_sha256(transcript.target_relation_digest, "target_relation_digest")
        _require_sha256(transcript.upstream_artifact_digest, "upstream_artifact_digest")
        _require_sha256(transcript.transcript_digest, "transcript_digest")
        _require_nonnegative_int(transcript.domain_degree, "domain_degree")
        _require_nonnegative_int(transcript.auxiliary_degree, "auxiliary_degree")
    except ParentOutcomeContractError as exc:
        return _closed(
            "fail_closed_malformed_parent_outcome_transcript",
            reason=str(exc),
            expected_source_relation_digest=expected_source_relation_digest,
            expected_target_relation_digest=expected_target_relation_digest,
            expected_domain_degree=expected_domain_degree,
        )
    if transcript.transcript_digest != _recompute_transcript_digest(transcript):
        return _closed(
            "fail_closed_corrupted_parent_outcome_transcript",
            reason="parent outcome transcript digest does not match its canonical fields",
            expected_source_relation_digest=expected_source_relation_digest,
            expected_target_relation_digest=expected_target_relation_digest,
            expected_domain_degree=expected_domain_degree,
        )
    if (
        transcript.source_relation_digest != expected_source_relation_digest
        or transcript.target_relation_digest != expected_target_relation_digest
        or transcript.domain_degree != expected_domain_degree
    ):
        return _closed(
            "fail_closed_parent_outcome_context_mismatch",
            reason="verified parent outcome is bound to a different source, target, or domain degree",
            expected_source_relation_digest=expected_source_relation_digest,
            expected_target_relation_digest=expected_target_relation_digest,
            expected_domain_degree=expected_domain_degree,
        )
    if transcript.exact is not True or transcript.complete is not True:
        return _closed(
            "fail_closed_parent_outcome_not_exact_complete",
            reason="parent outcome transcript is not both exact and complete",
            expected_source_relation_digest=expected_source_relation_digest,
            expected_target_relation_digest=expected_target_relation_digest,
            expected_domain_degree=expected_domain_degree,
        )

    if transcript.outcome_kind == "nonempty":
        if (
            transcript.source_evidence_revision != NONEMPTY_SOURCE_REVISION
            or transcript.source_evidence_status != NONEMPTY_STATUS
            or transcript.auxiliary_degree == 0
        ):
            return _closed(
                "fail_closed_nonempty_parent_outcome_contract",
                reason="nonempty outcome does not match the rev261 exact parent-coset contract",
                expected_source_relation_digest=expected_source_relation_digest,
                expected_target_relation_digest=expected_target_relation_digest,
                expected_domain_degree=expected_domain_degree,
            )
        return ParentExactOutcomeContract(
            status="exact_parent_outcome_nonempty",
            exact=True,
            complete=True,
            outcome_kind="nonempty",
            domain_degree=transcript.domain_degree,
            auxiliary_degree=transcript.auxiliary_degree,
            source_evidence_revision=transcript.source_evidence_revision,
            source_evidence_status=transcript.source_evidence_status,
            source_relation_digest=transcript.source_relation_digest,
            target_relation_digest=transcript.target_relation_digest,
            upstream_artifact_digest=transcript.upstream_artifact_digest,
            transcript_digest=transcript.transcript_digest,
            reason="one replay-stable exact complete rev261 nonempty parent transcript matches the requested relation context",
        )

    if transcript.outcome_kind == "exact_empty":
        if (
            transcript.source_evidence_revision != EXACT_EMPTY_SOURCE_REVISION
            or transcript.source_evidence_status not in EXACT_EMPTY_STATUSES
            or (
                transcript.source_evidence_status
                == "exact_empty_parent_feature_inventory_mismatch"
                and transcript.auxiliary_degree == 0
            )
        ):
            return _closed(
                "fail_closed_exact_empty_parent_outcome_contract",
                reason="exact-empty outcome does not match the rev263 exact-empty parent contract",
                expected_source_relation_digest=expected_source_relation_digest,
                expected_target_relation_digest=expected_target_relation_digest,
                expected_domain_degree=expected_domain_degree,
            )
        return ParentExactOutcomeContract(
            status="exact_parent_outcome_empty",
            exact=True,
            complete=True,
            outcome_kind="exact_empty",
            domain_degree=transcript.domain_degree,
            auxiliary_degree=transcript.auxiliary_degree,
            source_evidence_revision=transcript.source_evidence_revision,
            source_evidence_status=transcript.source_evidence_status,
            source_relation_digest=transcript.source_relation_digest,
            target_relation_digest=transcript.target_relation_digest,
            upstream_artifact_digest=transcript.upstream_artifact_digest,
            transcript_digest=transcript.transcript_digest,
            reason="one replay-stable exact complete rev263 exact-empty parent transcript matches the requested relation context",
        )

    return _closed(
        "fail_closed_unknown_parent_outcome_kind",
        reason="parent outcome kind is not recognized",
        expected_source_relation_digest=expected_source_relation_digest,
        expected_target_relation_digest=expected_target_relation_digest,
        expected_domain_degree=expected_domain_degree,
    )


__all__ = [
    "EXACT_EMPTY_STATUSES",
    "ParentExactOutcomeContract",
    "ParentOutcomeContractError",
    "ParentOutcomeTranscript",
    "normalize_parent_exact_outcome",
    "transcript_from_exact_empty_promotion",
    "transcript_from_nonempty_promotion",
]
