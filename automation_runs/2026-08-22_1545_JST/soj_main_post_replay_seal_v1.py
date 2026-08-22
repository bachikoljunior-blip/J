from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

SCHEMA_VERSION = 1
REV700_STATUS = "certified_corrected_soj_recursive_production_provenance_join"
REV1000_STATUS = "certified_recursive_production_post_replay_envelope"
OUTPUT_STATUS = "certified_corrected_soj_recursive_production_main_post_replay_seal"
_ALLOWED_RESULT_STATUS = frozenset({"exact_nonempty", "exact_empty"})
_ALLOWED_OUTCOMES = frozenset({"nonempty", "exact_empty"})
_BARE_SHA = re.compile(r"^[0-9a-f]{64}$")
_PREFIXED_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class MainPostReplaySeal:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    main_commit_sha: str
    main_provenance_identity: str
    caller_binding_identity: str
    caller_replay_envelope_identity: str
    outcome_kind: str
    parent_action_degree: int
    child_ground_size: int
    reduction_identity: str
    production_provenance_identity: str
    construction_cost_binding_identity: str
    construction_multiplicative_cost_bound: float
    charged_log2_reduction_cost: float
    post_replay_envelope_identity: str
    seal_identity: str
    reason: str


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        if name not in obj:
            raise ValueError(f"missing required field {name!r}")
        return obj[name]
    if not hasattr(obj, name):
        raise ValueError(f"missing required field {name!r}")
    return getattr(obj, name)


def _literal_true(value: Any, name: str) -> None:
    if type(value) is not bool or value is not True:
        raise ValueError(f"{name} must be literal true")


def _strict_int(value: Any, name: str, *, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be a strict integer >= {minimum}")
    return value


def _bare_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _BARE_SHA.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase 64-hex SHA-256")
    return value


def _prefixed_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _PREFIXED_SHA.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase sha256:<64-hex>")
    return value


def _git_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _GIT_SHA.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase 40-hex Git SHA")
    return value


def _finite(value: Any, name: str, *, minimum: float = 0.0) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"{name} must be a finite real number")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return result


def _fail(reason: str) -> MainPostReplaySeal:
    return MainPostReplaySeal(
        SCHEMA_VERSION,
        "corrected_soj_recursive_production_main_post_replay_seal_not_certified",
        False,
        False,
        False,
        "",
        "",
        "",
        "",
        "undetermined",
        0,
        0,
        "",
        "",
        "",
        0.0,
        0.0,
        "",
        "",
        reason,
    )


def _normalize_rev700(certificate: Any, replay_verified: bool) -> dict[str, Any]:
    _literal_true(replay_verified, "production_provenance_replay_verified")
    if _field(certificate, "schema_version") != 1:
        raise ValueError("rev700 schema_version mismatch")
    if _field(certificate, "status") != REV700_STATUS:
        raise ValueError("rev700 status mismatch")
    _literal_true(_field(certificate, "certified"), "rev700.certified")
    _literal_true(
        _field(certificate, "exact_contract_join"), "rev700.exact_contract_join"
    )
    result_status = _field(certificate, "result_status")
    if not isinstance(result_status, str) or result_status not in _ALLOWED_RESULT_STATUS:
        raise ValueError("rev700 result_status is unsupported")
    payload = {
        "schema_version": 1,
        "status": REV700_STATUS,
        "main_commit_sha": _git_sha(
            _field(certificate, "main_commit_sha"), "rev700.main_commit_sha"
        ),
        "caller_binding_identity": _bare_sha(
            _field(certificate, "caller_binding_identity"),
            "rev700.caller_binding_identity",
        ),
        "envelope_identity": _bare_sha(
            _field(certificate, "envelope_identity"), "rev700.envelope_identity"
        ),
        "main_provenance_identity": _bare_sha(
            _field(certificate, "main_provenance_identity"),
            "rev700.main_provenance_identity",
        ),
        "recursive_provenance_identity": _prefixed_sha(
            _field(certificate, "recursive_provenance_identity"),
            "rev700.recursive_provenance_identity",
        ),
        "result_status": result_status,
        "result_lift_digest": _prefixed_sha(
            _field(certificate, "result_lift_digest"), "rev700.result_lift_digest"
        ),
        "accounting_binding_digest": _prefixed_sha(
            _field(certificate, "accounting_binding_digest"),
            "rev700.accounting_binding_digest",
        ),
        "reduction_identity": _prefixed_sha(
            _field(certificate, "reduction_identity"), "rev700.reduction_identity"
        ),
        "child_result_identity": _prefixed_sha(
            _field(certificate, "child_result_identity"),
            "rev700.child_result_identity",
        ),
    }
    observed = _prefixed_sha(
        _field(certificate, "production_provenance_identity"),
        "rev700.production_provenance_identity",
    )
    if _canonical_hash(payload) != observed:
        raise ValueError("rev700 production_provenance_identity does not replay")
    return payload | {"production_provenance_identity": observed}


def _normalize_rev1000(envelope: Any, replay_verified: bool) -> dict[str, Any]:
    _literal_true(replay_verified, "post_replay_envelope_replay_verified")
    if _field(envelope, "schema_version") != 1:
        raise ValueError("rev1000 schema_version mismatch")
    if _field(envelope, "status") != REV1000_STATUS:
        raise ValueError("rev1000 status mismatch")
    _literal_true(_field(envelope, "certified"), "rev1000.certified")
    _literal_true(_field(envelope, "exact"), "rev1000.exact")
    _literal_true(_field(envelope, "complete"), "rev1000.complete")
    outcome = _field(envelope, "outcome_kind")
    if not isinstance(outcome, str) or outcome not in _ALLOWED_OUTCOMES:
        raise ValueError("rev1000 outcome_kind is unsupported")
    parent = _strict_int(
        _field(envelope, "parent_action_degree"), "rev1000.parent_action_degree"
    )
    child = _strict_int(
        _field(envelope, "child_ground_size"), "rev1000.child_ground_size"
    )
    if child >= parent:
        raise ValueError("rev1000 child_ground_size must be strictly smaller than parent")
    bound = _finite(
        _field(envelope, "construction_multiplicative_cost_bound"),
        "rev1000.construction_multiplicative_cost_bound",
        minimum=1.0,
    )
    charge = _finite(
        _field(envelope, "charged_log2_reduction_cost"),
        "rev1000.charged_log2_reduction_cost",
    )
    if not bound.is_integer():
        raise ValueError("rev1000 construction cost bound must be integral")
    bound_int = int(bound)
    if bound_int < 1 or bound_int & (bound_int - 1):
        raise ValueError("rev1000 construction cost bound must be a power of two")
    if charge != float(bound_int.bit_length() - 1):
        raise ValueError("rev1000 charged reduction cost must equal exact log2 bound")
    return {
        "outcome_kind": outcome,
        "parent_action_degree": parent,
        "child_ground_size": child,
        "reduction_identity": _prefixed_sha(
            _field(envelope, "reduction_identity"), "rev1000.reduction_identity"
        ),
        "production_provenance_identity": _prefixed_sha(
            _field(envelope, "production_provenance_identity"),
            "rev1000.production_provenance_identity",
        ),
        "construction_cost_binding_identity": _prefixed_sha(
            _field(envelope, "construction_cost_binding_identity"),
            "rev1000.construction_cost_binding_identity",
        ),
        "construction_multiplicative_cost_bound": bound,
        "charged_log2_reduction_cost": charge,
        "post_replay_envelope_identity": _prefixed_sha(
            _field(envelope, "envelope_identity"), "rev1000.envelope_identity"
        ),
    }


def certify_main_post_replay_seal(
    recursive_production_provenance: Any,
    post_replay_envelope: Any,
    *,
    production_provenance_replay_verified: bool,
    post_replay_envelope_replay_verified: bool,
) -> MainPostReplaySeal:
    """Seal a rev700 main anchor to a rev1000 cost/coherence post-replay envelope."""
    try:
        provenance = _normalize_rev700(
            recursive_production_provenance, production_provenance_replay_verified
        )
        post = _normalize_rev1000(
            post_replay_envelope, post_replay_envelope_replay_verified
        )
    except (TypeError, ValueError, OverflowError) as exc:
        return _fail(str(exc))

    expected_outcome = (
        "nonempty" if provenance["result_status"] == "exact_nonempty" else "exact_empty"
    )
    if post["outcome_kind"] != expected_outcome:
        return _fail("rev700 result status and rev1000 outcome kind disagree")
    if provenance["reduction_identity"] != post["reduction_identity"]:
        return _fail("rev700 and rev1000 disagree on reduction identity")
    if provenance["production_provenance_identity"] != post["production_provenance_identity"]:
        return _fail("rev1000 is not bound to the supplied replayed rev700 provenance join")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": OUTPUT_STATUS,
        "main_commit_sha": provenance["main_commit_sha"],
        "main_provenance_identity": provenance["main_provenance_identity"],
        "caller_binding_identity": provenance["caller_binding_identity"],
        "caller_replay_envelope_identity": provenance["envelope_identity"],
        "outcome_kind": post["outcome_kind"],
        "parent_action_degree": post["parent_action_degree"],
        "child_ground_size": post["child_ground_size"],
        "reduction_identity": post["reduction_identity"],
        "production_provenance_identity": post["production_provenance_identity"],
        "construction_cost_binding_identity": post["construction_cost_binding_identity"],
        "construction_multiplicative_cost_bound": post[
            "construction_multiplicative_cost_bound"
        ],
        "charged_log2_reduction_cost": post["charged_log2_reduction_cost"],
        "post_replay_envelope_identity": post["post_replay_envelope_identity"],
    }
    seal_identity = _canonical_hash(payload)
    return MainPostReplaySeal(
        SCHEMA_VERSION,
        OUTPUT_STATUS,
        True,
        True,
        True,
        provenance["main_commit_sha"],
        provenance["main_provenance_identity"],
        provenance["caller_binding_identity"],
        provenance["envelope_identity"],
        post["outcome_kind"],
        post["parent_action_degree"],
        post["child_ground_size"],
        post["reduction_identity"],
        post["production_provenance_identity"],
        post["construction_cost_binding_identity"],
        post["construction_multiplicative_cost_bound"],
        post["charged_log2_reduction_cost"],
        post["post_replay_envelope_identity"],
        seal_identity,
        "replayed main-anchored recursive production provenance and replayed post-cost envelope agree on one exact reduction/outcome chain",
    )


def replay_main_post_replay_seal(
    seal: MainPostReplaySeal,
    recursive_production_provenance: Any,
    post_replay_envelope: Any,
    *,
    production_provenance_replay_verified: bool,
    post_replay_envelope_replay_verified: bool,
) -> bool:
    if not isinstance(seal, MainPostReplaySeal):
        return False
    if seal.status != OUTPUT_STATUS or not seal.certified:
        return False
    rebuilt = certify_main_post_replay_seal(
        recursive_production_provenance,
        post_replay_envelope,
        production_provenance_replay_verified=production_provenance_replay_verified,
        post_replay_envelope_replay_verified=post_replay_envelope_replay_verified,
    )
    return bool(rebuilt.certified and rebuilt == seal and rebuilt.seal_identity == seal.seal_identity)


__all__ = [
    "MainPostReplaySeal",
    "certify_main_post_replay_seal",
    "replay_main_post_replay_seal",
]
