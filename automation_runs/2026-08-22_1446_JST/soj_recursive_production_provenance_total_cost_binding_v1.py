from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

REV700_STATUS = "certified_corrected_soj_recursive_production_provenance_join"
REV800_STATUS = "certified_recursive_production_total_cost_coherence"
OUTPUT_STATUS = "certified_recursive_production_provenance_total_cost_binding"

_SHA256_BARE_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA256_PREFIXED_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class RecursiveProductionProvenanceTotalCostBinding:
    schema_version: int
    status: str
    certified: bool
    exact_contract_binding: bool
    main_commit_sha: str
    caller_binding_identity: str
    envelope_identity: str
    main_provenance_identity: str
    recursive_provenance_identity: str
    production_provenance_identity: str
    result_status: str
    result_lift_digest: str
    accounting_binding_digest: str
    reduction_identity: str
    child_result_identity: str
    coherence_identity: str
    parent_action_degree: int
    child_ground_size: int
    construction_cost_binding_identity: str
    construction_multiplicative_cost_bound: float
    charged_log2_reduction_cost: float
    total_cost_binding_identity: str
    reason: str


def _fail(reason: str) -> RecursiveProductionProvenanceTotalCostBinding:
    return RecursiveProductionProvenanceTotalCostBinding(
        1,
        "recursive_production_provenance_total_cost_binding_not_certified",
        False,
        False,
        "",
        "",
        "",
        "",
        "",
        "",
        "undetermined",
        "",
        "",
        "",
        "",
        "",
        0,
        0,
        "",
        0.0,
        0.0,
        "",
        reason,
    )


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


def _strict_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _finite_number(value: Any, name: str, *, minimum: float = 0.0) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"{name} must be a finite real number")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return number


def _bare_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SHA256_BARE_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase 64-hex SHA-256")
    return value


def _prefixed_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SHA256_PREFIXED_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase sha256:<64-hex>")
    return value


def _git_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _GIT_SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase 40-hex Git SHA")
    return value


def _prefixed_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _normalize_rev700(certificate: Any, replay_verified: bool) -> dict[str, Any]:
    _literal_true(replay_verified, "rev700_replay_verified")
    if _strict_int(_field(certificate, "schema_version"), "rev700.schema_version") != 1:
        raise ValueError("rev700 schema version mismatch")
    if _field(certificate, "status") != REV700_STATUS:
        raise ValueError("rev700 status mismatch")
    _literal_true(_field(certificate, "certified"), "rev700.certified")
    _literal_true(_field(certificate, "exact_contract_join"), "rev700.exact_contract_join")

    result_status = _field(certificate, "result_status")
    if result_status not in {"exact_nonempty", "exact_empty"} or not isinstance(result_status, str):
        raise ValueError("rev700 result_status is unsupported")

    payload = {
        "schema_version": 1,
        "status": REV700_STATUS,
        "main_commit_sha": _git_sha(_field(certificate, "main_commit_sha"), "rev700.main_commit_sha"),
        "caller_binding_identity": _bare_sha(
            _field(certificate, "caller_binding_identity"), "rev700.caller_binding_identity"
        ),
        "envelope_identity": _bare_sha(
            _field(certificate, "envelope_identity"), "rev700.envelope_identity"
        ),
        "main_provenance_identity": _bare_sha(
            _field(certificate, "main_provenance_identity"), "rev700.main_provenance_identity"
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
            _field(certificate, "child_result_identity"), "rev700.child_result_identity"
        ),
    }
    observed = _prefixed_sha(
        _field(certificate, "production_provenance_identity"),
        "rev700.production_provenance_identity",
    )
    if _prefixed_digest(payload) != observed:
        raise ValueError("rev700 production_provenance_identity replay failed")
    payload["production_provenance_identity"] = observed
    return payload


def _normalize_rev800(certificate: Any, replay_verified: bool) -> dict[str, Any]:
    _literal_true(replay_verified, "rev800_replay_verified")
    if _strict_int(_field(certificate, "schema_version"), "rev800.schema_version") != 1:
        raise ValueError("rev800 schema version mismatch")
    if _field(certificate, "status") != REV800_STATUS:
        raise ValueError("rev800 status mismatch")
    for field in ("certified", "exact", "complete"):
        _literal_true(_field(certificate, field), f"rev800.{field}")

    outcome_kind = _field(certificate, "outcome_kind")
    if outcome_kind not in {"nonempty", "exact_empty"} or not isinstance(outcome_kind, str):
        raise ValueError("rev800 outcome_kind is unsupported")

    parent = _strict_int(
        _field(certificate, "parent_action_degree"),
        "rev800.parent_action_degree",
        minimum=1,
    )
    child = _strict_int(
        _field(certificate, "child_ground_size"),
        "rev800.child_ground_size",
        minimum=1,
    )
    if child >= parent:
        raise ValueError("rev800 must certify strict recursive shrink")

    construction_bound = _finite_number(
        _field(certificate, "construction_multiplicative_cost_bound"),
        "rev800.construction_multiplicative_cost_bound",
        minimum=1.0,
    )
    charged = _finite_number(
        _field(certificate, "charged_log2_reduction_cost"),
        "rev800.charged_log2_reduction_cost",
        minimum=0.0,
    )
    if not construction_bound.is_integer():
        raise ValueError("rev800 construction bound must remain an integral power of two")
    integral_bound = int(construction_bound)
    if integral_bound < 1 or integral_bound & (integral_bound - 1):
        raise ValueError("rev800 construction bound must remain a power of two")
    exact_charge = float(integral_bound.bit_length() - 1)
    if charged != exact_charge:
        raise ValueError("rev800 charge must remain exactly log2 of its construction bound")

    payload = {
        "schema_version": 1,
        "status": REV800_STATUS,
        "outcome_kind": outcome_kind,
        "parent_action_degree": parent,
        "child_ground_size": child,
        "reduction_identity": _prefixed_sha(
            _field(certificate, "reduction_identity"), "rev800.reduction_identity"
        ),
        "accounting_binding_digest": _prefixed_sha(
            _field(certificate, "accounting_binding_digest"),
            "rev800.accounting_binding_digest",
        ),
        "construction_cost_binding_identity": _prefixed_sha(
            _field(certificate, "construction_cost_binding_identity"),
            "rev800.construction_cost_binding_identity",
        ),
        "construction_multiplicative_cost_bound": construction_bound,
        "charged_log2_reduction_cost": charged,
    }
    observed = _prefixed_sha(
        _field(certificate, "coherence_identity"), "rev800.coherence_identity"
    )
    if _prefixed_digest(payload) != observed:
        raise ValueError("rev800 coherence_identity replay failed")
    payload["coherence_identity"] = observed
    return payload


def certify_recursive_production_provenance_total_cost_binding(
    production_provenance: Any,
    total_cost_coherence: Any,
    *,
    production_provenance_replay_verified: bool,
    total_cost_coherence_replay_verified: bool,
) -> RecursiveProductionProvenanceTotalCostBinding:
    """Bind rev700 provenance to the exact rev800 accounting/cost certificate it authenticates."""
    try:
        provenance = _normalize_rev700(
            production_provenance, production_provenance_replay_verified
        )
        coherence = _normalize_rev800(
            total_cost_coherence, total_cost_coherence_replay_verified
        )
    except (TypeError, ValueError) as exc:
        return _fail(str(exc))

    if provenance["accounting_binding_digest"] != coherence["accounting_binding_digest"]:
        return _fail("rev700 and rev800 disagree on accounting-binding digest")
    if provenance["reduction_identity"] != coherence["reduction_identity"]:
        return _fail("rev700 and rev800 disagree on reduction identity")

    expected_outcome = (
        "exact_empty" if provenance["result_status"] == "exact_empty" else "nonempty"
    )
    if coherence["outcome_kind"] != expected_outcome:
        return _fail(
            "rev700 result status and rev800 outcome kind do not preserve the same exact-empty/nonempty semantics"
        )

    payload = {
        "schema_version": 1,
        "status": OUTPUT_STATUS,
        "main_commit_sha": provenance["main_commit_sha"],
        "caller_binding_identity": provenance["caller_binding_identity"],
        "envelope_identity": provenance["envelope_identity"],
        "main_provenance_identity": provenance["main_provenance_identity"],
        "recursive_provenance_identity": provenance["recursive_provenance_identity"],
        "production_provenance_identity": provenance["production_provenance_identity"],
        "result_status": provenance["result_status"],
        "result_lift_digest": provenance["result_lift_digest"],
        "accounting_binding_digest": provenance["accounting_binding_digest"],
        "reduction_identity": provenance["reduction_identity"],
        "child_result_identity": provenance["child_result_identity"],
        "coherence_identity": coherence["coherence_identity"],
        "parent_action_degree": coherence["parent_action_degree"],
        "child_ground_size": coherence["child_ground_size"],
        "construction_cost_binding_identity": coherence[
            "construction_cost_binding_identity"
        ],
        "construction_multiplicative_cost_bound": coherence[
            "construction_multiplicative_cost_bound"
        ],
        "charged_log2_reduction_cost": coherence["charged_log2_reduction_cost"],
    }
    identity = _prefixed_digest(payload)
    return RecursiveProductionProvenanceTotalCostBinding(
        1,
        OUTPUT_STATUS,
        True,
        True,
        payload["main_commit_sha"],
        payload["caller_binding_identity"],
        payload["envelope_identity"],
        payload["main_provenance_identity"],
        payload["recursive_provenance_identity"],
        payload["production_provenance_identity"],
        payload["result_status"],
        payload["result_lift_digest"],
        payload["accounting_binding_digest"],
        payload["reduction_identity"],
        payload["child_result_identity"],
        payload["coherence_identity"],
        payload["parent_action_degree"],
        payload["child_ground_size"],
        payload["construction_cost_binding_identity"],
        payload["construction_multiplicative_cost_bound"],
        payload["charged_log2_reduction_cost"],
        identity,
        "replayed rev700 production provenance and rev800 total-cost coherence authenticate the same reduction/accounting chain and preserve one exact-empty/nonempty outcome while retaining the exactly-once construction charge",
    )


def replay_recursive_production_provenance_total_cost_binding(
    certificate: RecursiveProductionProvenanceTotalCostBinding,
    production_provenance: Any,
    total_cost_coherence: Any,
    *,
    production_provenance_replay_verified: bool,
    total_cost_coherence_replay_verified: bool,
) -> bool:
    if not isinstance(certificate, RecursiveProductionProvenanceTotalCostBinding):
        return False
    if (
        certificate.schema_version != 1
        or not certificate.certified
        or not certificate.exact_contract_binding
    ):
        return False
    replay = certify_recursive_production_provenance_total_cost_binding(
        production_provenance,
        total_cost_coherence,
        production_provenance_replay_verified=production_provenance_replay_verified,
        total_cost_coherence_replay_verified=total_cost_coherence_replay_verified,
    )
    return bool(
        replay.certified
        and replay == certificate
        and replay.total_cost_binding_identity == certificate.total_cost_binding_identity
    )


__all__ = [
    "RecursiveProductionProvenanceTotalCostBinding",
    "certify_recursive_production_provenance_total_cost_binding",
    "replay_recursive_production_provenance_total_cost_binding",
]
