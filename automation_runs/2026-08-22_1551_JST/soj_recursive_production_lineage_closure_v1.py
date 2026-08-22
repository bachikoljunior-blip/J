from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

SCHEMA_VERSION = 1
REV900_STATUS = "certified_recursive_production_provenance_total_cost_binding"
REV1100_STATUS = "certified_corrected_soj_recursive_production_main_post_replay_seal"
OUTPUT_STATUS = "certified_corrected_soj_recursive_production_lineage_closure"
_ALLOWED_RESULT_STATUS = frozenset({"exact_nonempty", "exact_empty"})
_ALLOWED_OUTCOMES = frozenset({"nonempty", "exact_empty"})
_BARE_SHA = re.compile(r"^[0-9a-f]{64}$")
_PREFIXED_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class RecursiveProductionLineageClosure:
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
    recursive_provenance_identity: str
    result_lift_digest: str
    accounting_binding_digest: str
    child_result_identity: str
    coherence_identity: str
    construction_cost_binding_identity: str
    construction_multiplicative_cost_bound: float
    charged_log2_reduction_cost: float
    total_cost_binding_identity: str
    post_replay_envelope_identity: str
    main_post_replay_seal_identity: str
    closure_identity: str
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


def _power_of_two_cost(bound_value: Any, charge_value: Any, prefix: str) -> tuple[float, float]:
    bound = _finite(bound_value, f"{prefix}.construction_multiplicative_cost_bound", minimum=1.0)
    charge = _finite(charge_value, f"{prefix}.charged_log2_reduction_cost")
    if not bound.is_integer():
        raise ValueError(f"{prefix} construction cost bound must be integral")
    bound_int = int(bound)
    if bound_int < 1 or bound_int & (bound_int - 1):
        raise ValueError(f"{prefix} construction cost bound must be a power of two")
    expected = float(bound_int.bit_length() - 1)
    if charge != expected:
        raise ValueError(f"{prefix} charged reduction cost must equal exact log2 bound")
    return bound, charge


def _fail(reason: str) -> RecursiveProductionLineageClosure:
    return RecursiveProductionLineageClosure(
        SCHEMA_VERSION,
        "corrected_soj_recursive_production_lineage_closure_not_certified",
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
        "",
        "",
        "",
        "",
        "",
        0.0,
        0.0,
        "",
        "",
        "",
        "",
        reason,
    )


def _normalize_rev900(certificate: Any) -> dict[str, Any]:
    if _field(certificate, "schema_version") != SCHEMA_VERSION:
        raise ValueError("rev900 schema_version mismatch")
    if _field(certificate, "status") != REV900_STATUS:
        raise ValueError("rev900 status mismatch")
    _literal_true(_field(certificate, "certified"), "rev900.certified")
    _literal_true(
        _field(certificate, "exact_contract_binding"),
        "rev900.exact_contract_binding",
    )
    result_status = _field(certificate, "result_status")
    if not isinstance(result_status, str) or result_status not in _ALLOWED_RESULT_STATUS:
        raise ValueError("rev900 result_status is unsupported")
    parent = _strict_int(
        _field(certificate, "parent_action_degree"),
        "rev900.parent_action_degree",
    )
    child = _strict_int(
        _field(certificate, "child_ground_size"),
        "rev900.child_ground_size",
    )
    if child >= parent:
        raise ValueError("rev900 must retain strict recursive shrink")
    bound, charge = _power_of_two_cost(
        _field(certificate, "construction_multiplicative_cost_bound"),
        _field(certificate, "charged_log2_reduction_cost"),
        "rev900",
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": REV900_STATUS,
        "main_commit_sha": _git_sha(
            _field(certificate, "main_commit_sha"), "rev900.main_commit_sha"
        ),
        "caller_binding_identity": _bare_sha(
            _field(certificate, "caller_binding_identity"),
            "rev900.caller_binding_identity",
        ),
        "envelope_identity": _bare_sha(
            _field(certificate, "envelope_identity"), "rev900.envelope_identity"
        ),
        "main_provenance_identity": _bare_sha(
            _field(certificate, "main_provenance_identity"),
            "rev900.main_provenance_identity",
        ),
        "recursive_provenance_identity": _prefixed_sha(
            _field(certificate, "recursive_provenance_identity"),
            "rev900.recursive_provenance_identity",
        ),
        "production_provenance_identity": _prefixed_sha(
            _field(certificate, "production_provenance_identity"),
            "rev900.production_provenance_identity",
        ),
        "result_status": result_status,
        "result_lift_digest": _prefixed_sha(
            _field(certificate, "result_lift_digest"), "rev900.result_lift_digest"
        ),
        "accounting_binding_digest": _prefixed_sha(
            _field(certificate, "accounting_binding_digest"),
            "rev900.accounting_binding_digest",
        ),
        "reduction_identity": _prefixed_sha(
            _field(certificate, "reduction_identity"), "rev900.reduction_identity"
        ),
        "child_result_identity": _prefixed_sha(
            _field(certificate, "child_result_identity"),
            "rev900.child_result_identity",
        ),
        "coherence_identity": _prefixed_sha(
            _field(certificate, "coherence_identity"), "rev900.coherence_identity"
        ),
        "parent_action_degree": parent,
        "child_ground_size": child,
        "construction_cost_binding_identity": _prefixed_sha(
            _field(certificate, "construction_cost_binding_identity"),
            "rev900.construction_cost_binding_identity",
        ),
        "construction_multiplicative_cost_bound": bound,
        "charged_log2_reduction_cost": charge,
    }
    observed = _prefixed_sha(
        _field(certificate, "total_cost_binding_identity"),
        "rev900.total_cost_binding_identity",
    )
    if _canonical_hash(payload) != observed:
        raise ValueError("rev900 total_cost_binding_identity replay failed")
    return payload | {"total_cost_binding_identity": observed}


def _normalize_rev1100(certificate: Any) -> dict[str, Any]:
    if _field(certificate, "schema_version") != SCHEMA_VERSION:
        raise ValueError("rev1100 schema_version mismatch")
    if _field(certificate, "status") != REV1100_STATUS:
        raise ValueError("rev1100 status mismatch")
    for field in ("certified", "exact", "complete"):
        _literal_true(_field(certificate, field), f"rev1100.{field}")
    outcome = _field(certificate, "outcome_kind")
    if not isinstance(outcome, str) or outcome not in _ALLOWED_OUTCOMES:
        raise ValueError("rev1100 outcome_kind is unsupported")
    parent = _strict_int(
        _field(certificate, "parent_action_degree"),
        "rev1100.parent_action_degree",
    )
    child = _strict_int(
        _field(certificate, "child_ground_size"),
        "rev1100.child_ground_size",
    )
    if child >= parent:
        raise ValueError("rev1100 must retain strict recursive shrink")
    bound, charge = _power_of_two_cost(
        _field(certificate, "construction_multiplicative_cost_bound"),
        _field(certificate, "charged_log2_reduction_cost"),
        "rev1100",
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": REV1100_STATUS,
        "main_commit_sha": _git_sha(
            _field(certificate, "main_commit_sha"), "rev1100.main_commit_sha"
        ),
        "main_provenance_identity": _bare_sha(
            _field(certificate, "main_provenance_identity"),
            "rev1100.main_provenance_identity",
        ),
        "caller_binding_identity": _bare_sha(
            _field(certificate, "caller_binding_identity"),
            "rev1100.caller_binding_identity",
        ),
        "caller_replay_envelope_identity": _bare_sha(
            _field(certificate, "caller_replay_envelope_identity"),
            "rev1100.caller_replay_envelope_identity",
        ),
        "outcome_kind": outcome,
        "parent_action_degree": parent,
        "child_ground_size": child,
        "reduction_identity": _prefixed_sha(
            _field(certificate, "reduction_identity"), "rev1100.reduction_identity"
        ),
        "production_provenance_identity": _prefixed_sha(
            _field(certificate, "production_provenance_identity"),
            "rev1100.production_provenance_identity",
        ),
        "construction_cost_binding_identity": _prefixed_sha(
            _field(certificate, "construction_cost_binding_identity"),
            "rev1100.construction_cost_binding_identity",
        ),
        "construction_multiplicative_cost_bound": bound,
        "charged_log2_reduction_cost": charge,
        "post_replay_envelope_identity": _prefixed_sha(
            _field(certificate, "post_replay_envelope_identity"),
            "rev1100.post_replay_envelope_identity",
        ),
    }
    observed = _prefixed_sha(
        _field(certificate, "seal_identity"), "rev1100.seal_identity"
    )
    if _canonical_hash(payload) != observed:
        raise ValueError("rev1100 seal_identity replay failed")
    return payload | {"seal_identity": observed}


def certify_recursive_production_lineage_closure(
    provenance_total_cost_binding: Any,
    main_post_replay_seal: Any,
) -> RecursiveProductionLineageClosure:
    """Close explicit lineage between independently replayable rev900 and rev1100 outputs.

    This adapter deliberately does not import either sibling implementation.  It
    replays only the deterministic public identity formulas and requires their
    shared semantic tuple to agree before retaining lineage fields that the
    compact rev1100 seal intentionally omits.
    """
    try:
        total = _normalize_rev900(provenance_total_cost_binding)
        seal = _normalize_rev1100(main_post_replay_seal)
    except (TypeError, ValueError, OverflowError) as exc:
        return _fail(str(exc))

    shared_equal = (
        ("main_commit_sha", "main commit"),
        ("main_provenance_identity", "main provenance identity"),
        ("caller_binding_identity", "caller binding identity"),
        ("reduction_identity", "reduction identity"),
        ("production_provenance_identity", "production provenance identity"),
        ("parent_action_degree", "parent action degree"),
        ("child_ground_size", "child ground size"),
        ("construction_cost_binding_identity", "construction-cost binding identity"),
        ("construction_multiplicative_cost_bound", "construction cost bound"),
        ("charged_log2_reduction_cost", "charged reduction cost"),
    )
    for field, label in shared_equal:
        if total[field] != seal[field]:
            return _fail(f"rev900 and rev1100 disagree on {label}")
    if total["envelope_identity"] != seal["caller_replay_envelope_identity"]:
        return _fail("rev900 caller replay envelope does not match rev1100")
    expected_outcome = (
        "nonempty" if total["result_status"] == "exact_nonempty" else "exact_empty"
    )
    if seal["outcome_kind"] != expected_outcome:
        return _fail("rev900 and rev1100 disagree on exact-empty/nonempty outcome")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": OUTPUT_STATUS,
        "main_commit_sha": total["main_commit_sha"],
        "main_provenance_identity": total["main_provenance_identity"],
        "caller_binding_identity": total["caller_binding_identity"],
        "caller_replay_envelope_identity": total["envelope_identity"],
        "outcome_kind": seal["outcome_kind"],
        "parent_action_degree": total["parent_action_degree"],
        "child_ground_size": total["child_ground_size"],
        "reduction_identity": total["reduction_identity"],
        "production_provenance_identity": total["production_provenance_identity"],
        "recursive_provenance_identity": total["recursive_provenance_identity"],
        "result_lift_digest": total["result_lift_digest"],
        "accounting_binding_digest": total["accounting_binding_digest"],
        "child_result_identity": total["child_result_identity"],
        "coherence_identity": total["coherence_identity"],
        "construction_cost_binding_identity": total[
            "construction_cost_binding_identity"
        ],
        "construction_multiplicative_cost_bound": total[
            "construction_multiplicative_cost_bound"
        ],
        "charged_log2_reduction_cost": total["charged_log2_reduction_cost"],
        "total_cost_binding_identity": total["total_cost_binding_identity"],
        "post_replay_envelope_identity": seal["post_replay_envelope_identity"],
        "main_post_replay_seal_identity": seal["seal_identity"],
    }
    identity = _canonical_hash(payload)
    return RecursiveProductionLineageClosure(
        SCHEMA_VERSION,
        OUTPUT_STATUS,
        True,
        True,
        True,
        payload["main_commit_sha"],
        payload["main_provenance_identity"],
        payload["caller_binding_identity"],
        payload["caller_replay_envelope_identity"],
        payload["outcome_kind"],
        payload["parent_action_degree"],
        payload["child_ground_size"],
        payload["reduction_identity"],
        payload["production_provenance_identity"],
        payload["recursive_provenance_identity"],
        payload["result_lift_digest"],
        payload["accounting_binding_digest"],
        payload["child_result_identity"],
        payload["coherence_identity"],
        payload["construction_cost_binding_identity"],
        payload["construction_multiplicative_cost_bound"],
        payload["charged_log2_reduction_cost"],
        payload["total_cost_binding_identity"],
        payload["post_replay_envelope_identity"],
        payload["main_post_replay_seal_identity"],
        identity,
        "rev900 total-cost lineage and rev1100 main post-replay seal independently replay and agree on one main-anchored recursive reduction/outcome/cost chain",
    )


def replay_recursive_production_lineage_closure(
    closure: RecursiveProductionLineageClosure,
    provenance_total_cost_binding: Any,
    main_post_replay_seal: Any,
) -> bool:
    if not isinstance(closure, RecursiveProductionLineageClosure):
        return False
    if (
        closure.schema_version != SCHEMA_VERSION
        or closure.status != OUTPUT_STATUS
        or not closure.certified
        or not closure.exact
        or not closure.complete
    ):
        return False
    rebuilt = certify_recursive_production_lineage_closure(
        provenance_total_cost_binding, main_post_replay_seal
    )
    return bool(
        rebuilt.certified
        and rebuilt == closure
        and rebuilt.closure_identity == closure.closure_identity
    )


__all__ = [
    "RecursiveProductionLineageClosure",
    "certify_recursive_production_lineage_closure",
    "replay_recursive_production_lineage_closure",
]
