from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 1
PARENT_NONEMPTY_STATUS = "exact_parent_filtered_ground_coset"
PARENT_EMPTY_STATUS = "exact_empty_parent_filtered_ground_coset"
EXEC_NONEMPTY_STATUS = "certified_recursive_production_execution_parent_coset"
EXEC_EMPTY_STATUS = "certified_recursive_production_execution_parent_empty"
OUTPUT_STATUS = "certified_parent_filtered_child_execution_proof_dag_binding"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ParentFilteredExecutionProofDAGBinding:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    parent_outcome_kind: str
    proof_dag_outcome_kind: str
    reduction_identity: str
    child_result_identity: str
    parent_filtered_result_identity: str
    execution_closure_identity: str
    execution_result_lift_digest: str
    execution_proof_identity_digest: str
    child_proof_identity_digest: str
    child_ground_size: int
    same_child_execution_certified: bool
    parent_result_identity_equivalence_certified: bool
    binding_identity: str
    reason: str


def _fail(reason: str) -> ParentFilteredExecutionProofDAGBinding:
    return ParentFilteredExecutionProofDAGBinding(
        SCHEMA_VERSION,
        "parent_filtered_child_execution_proof_dag_binding_not_certified",
        False,
        False,
        False,
        "undetermined",
        "undetermined",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        0,
        False,
        False,
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


def _strict_true(obj: Any, name: str) -> None:
    if type(_field(obj, name)) is not bool or _field(obj, name) is not True:
        raise ValueError(f"{name} must be literal true")


def _strict_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be a strict integer >= {minimum}")
    return value


def _prefixed_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase sha256:<64-hex>")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _perm(raw: Any, degree: int, name: str) -> tuple[int, ...]:
    seq = _sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong degree")
    out = tuple(_strict_int(x, f"{name}[{i}]", minimum=0) for i, x in enumerate(seq))
    if any(x >= degree for x in out) or len(set(out)) != degree:
        raise ValueError(f"{name} is not a permutation")
    return out


def _stable(value: Any, path: str = "value") -> Any:
    if dataclasses.is_dataclass(value):
        value = {f.name: getattr(value, f.name) for f in dataclasses.fields(value)}
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} float must be finite")
        return value
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value):
            if type(key) is not str:
                raise ValueError(f"{path} mapping keys must be strings")
            out[key] = _stable(value[key], f"{path}.{key}")
        return out
    if isinstance(value, (list, tuple)):
        return [_stable(item, f"{path}[{i}]") for i, item in enumerate(value)]
    if hasattr(value, "__dict__"):
        public = {k: v for k, v in vars(value).items() if not k.startswith("_")}
        if not public:
            raise ValueError(f"{path} has opaque/non-replay-stable type {type(value).__name__}")
        return _stable(public, path)
    raise ValueError(f"{path} has opaque/non-replay-stable type {type(value).__name__}")


def _sha256(value: Any) -> str:
    raw = json.dumps(
        _stable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _normalize_parent_filtered(result: Any) -> dict[str, Any]:
    if _field(result, "schema_version") != SCHEMA_VERSION:
        raise ValueError("rev2200 schema_version mismatch")
    status = _field(result, "status")
    if status not in {PARENT_NONEMPTY_STATUS, PARENT_EMPTY_STATUS}:
        raise ValueError("rev2200 parent-filtered status mismatch")
    for name in ("certified", "exact", "complete"):
        _strict_true(result, name)

    reduction = _prefixed_sha(_field(result, "reduction_identity"), "rev2200.reduction_identity")
    semantic = _prefixed_sha(_field(result, "semantic_binding_identity"), "rev2200.semantic_binding_identity")
    child_instance = _prefixed_sha(_field(result, "child_instance_identity"), "rev2200.child_instance_identity")
    child_result = _prefixed_sha(_field(result, "child_result_identity"), "rev2200.child_result_identity")
    degree = _strict_int(_field(result, "action_degree"), "rev2200.action_degree", minimum=1)
    candidate_count = _strict_int(_field(result, "candidate_count"), "rev2200.candidate_count")
    accepted_count = _strict_int(_field(result, "accepted_count"), "rev2200.accepted_count")
    if accepted_count > candidate_count:
        raise ValueError("rev2200 accepted_count exceeds candidate_count")
    work_bound = _strict_int(_field(result, "work_bound"), "rev2200.work_bound")

    raw_rep = _field(result, "representative")
    raw_stabilizer = _field(result, "parent_stabilizer_elements")
    if status == PARENT_EMPTY_STATUS:
        if accepted_count != 0 or raw_rep is not None or tuple(raw_stabilizer) != ():
            raise ValueError("rev2200 exact-empty result carries nonempty coset data")
        rep = None
        stabilizer: tuple[tuple[int, ...], ...] = ()
        parent_outcome = "exact_empty"
    else:
        if accepted_count < 1 or raw_rep is None:
            raise ValueError("rev2200 nonempty result lacks accepted representative")
        rep = _perm(raw_rep, degree, "rev2200.representative")
        stabilizer = tuple(
            _perm(item, degree, f"rev2200.parent_stabilizer_elements[{i}]")
            for i, item in enumerate(_sequence(raw_stabilizer, "rev2200.parent_stabilizer_elements"))
        )
        if stabilizer != tuple(sorted(set(stabilizer))):
            raise ValueError("rev2200 parent stabilizer elements must be canonical sorted unique")
        parent_outcome = "nonempty"

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reduction_identity": reduction,
        "semantic_binding_identity": semantic,
        "child_instance_identity": child_instance,
        "child_result_identity": child_result,
        "action_degree": degree,
        "candidate_count": candidate_count,
        "accepted_count": accepted_count,
        "representative": rep,
        "parent_stabilizer_elements": stabilizer,
        "work_bound": work_bound,
    }
    observed = _prefixed_sha(_field(result, "result_identity"), "rev2200.result_identity")
    if _sha256(payload) != observed:
        raise ValueError("rev2200 result_identity replay failed")
    return payload | {"result_identity": observed, "parent_outcome": parent_outcome}


def _normalize_execution(result: Any) -> dict[str, Any]:
    if _field(result, "schema_version") != SCHEMA_VERSION:
        raise ValueError("rev1400 schema_version mismatch")
    status = _field(result, "status")
    if status not in {EXEC_NONEMPTY_STATUS, EXEC_EMPTY_STATUS}:
        raise ValueError("rev1400 execution status mismatch")
    for name in ("certified", "exact", "complete"):
        _strict_true(result, name)

    outcome = _field(result, "outcome_kind")
    expected_outcome = "nonempty" if status == EXEC_NONEMPTY_STATUS else "exact_empty"
    if outcome != expected_outcome:
        raise ValueError("rev1400 outcome_kind disagrees with status")
    parent_degree = _strict_int(_field(result, "parent_action_degree"), "rev1400.parent_action_degree", minimum=1)
    child_degree = _strict_int(_field(result, "child_ground_size"), "rev1400.child_ground_size", minimum=1)
    if child_degree >= parent_degree:
        raise ValueError("rev1400 execution must retain strict parent-to-child shrink")
    reduction = _prefixed_sha(_field(result, "reduction_identity"), "rev1400.reduction_identity")
    closure = _prefixed_sha(_field(result, "closure_identity"), "rev1400.closure_identity")
    child_result = _prefixed_sha(_field(result, "child_result_identity"), "rev1400.child_result_identity")
    lift = _prefixed_sha(_field(result, "result_lift_digest"), "rev1400.result_lift_digest")

    proof_identity = _field(result, "proof_identity")
    if proof_identity is None:
        raise ValueError("rev1400 proof_identity is required")
    if _field(proof_identity, "closure_identity") != closure:
        raise ValueError("rev1400 proof_identity closure_identity mismatch")
    if _field(proof_identity, "result_lift_digest") != lift:
        raise ValueError("rev1400 proof_identity result_lift_digest mismatch")
    if _field(proof_identity, "child_result_identity") != child_result:
        raise ValueError("rev1400 proof_identity child_result_identity mismatch")
    _strict_true(proof_identity, "replay_stable")
    original_root_n = _strict_int(_field(proof_identity, "original_root_n"), "rev1400.proof_identity.original_root_n", minimum=1)
    if original_root_n < parent_degree:
        raise ValueError("rev1400 proof_identity original_root_n must dominate parent degree")
    child_proof_identity = _field(proof_identity, "child_proof_identity")
    if child_proof_identity is None:
        raise ValueError("rev1400 child_proof_identity is required")
    if isinstance(child_proof_identity, Mapping) and "replay_stable" in child_proof_identity:
        _strict_true(child_proof_identity, "replay_stable")
    elif hasattr(child_proof_identity, "replay_stable"):
        _strict_true(child_proof_identity, "replay_stable")
    proof_digest = _sha256(proof_identity)
    child_proof_digest = _sha256(child_proof_identity)

    return {
        "status": status,
        "outcome": outcome,
        "parent_degree": parent_degree,
        "child_degree": child_degree,
        "reduction_identity": reduction,
        "closure_identity": closure,
        "child_result_identity": child_result,
        "result_lift_digest": lift,
        "proof_identity_digest": proof_digest,
        "child_proof_identity_digest": child_proof_digest,
    }


def certify_parent_filtered_execution_proof_dag_binding(
    parent_filtered_result: Any,
    execution_proof_dag_result: Any,
) -> ParentFilteredExecutionProofDAGBinding:
    try:
        parent = _normalize_parent_filtered(parent_filtered_result)
        execution = _normalize_execution(execution_proof_dag_result)
        if parent["reduction_identity"] != execution["reduction_identity"]:
            raise ValueError("rev2200/rev1400 reduction_identity mismatch")
        if parent["child_result_identity"] != execution["child_result_identity"]:
            raise ValueError("rev2200/rev1400 child_result_identity mismatch")
        if parent["action_degree"] != execution["child_degree"]:
            raise ValueError("rev2200 action degree differs from rev1400 child ground size")
        if execution["outcome"] == "exact_empty":
            if parent["parent_outcome"] != "exact_empty":
                raise ValueError("rev1400 exact-empty child execution cannot bind to a nonempty rev2200 parent result")
            if parent["candidate_count"] != 0:
                raise ValueError("rev1400 exact-empty child execution requires zero rev2200 candidates")

        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": OUTPUT_STATUS,
            "parent_outcome_kind": parent["parent_outcome"],
            "proof_dag_outcome_kind": execution["outcome"],
            "reduction_identity": parent["reduction_identity"],
            "child_result_identity": parent["child_result_identity"],
            "parent_filtered_result_identity": parent["result_identity"],
            "execution_closure_identity": execution["closure_identity"],
            "execution_result_lift_digest": execution["result_lift_digest"],
            "execution_proof_identity_digest": execution["proof_identity_digest"],
            "child_proof_identity_digest": execution["child_proof_identity_digest"],
            "child_ground_size": execution["child_degree"],
            "same_child_execution_certified": True,
            "parent_result_identity_equivalence_certified": False,
        }
        binding_identity = _sha256(payload)
    except (TypeError, ValueError, OverflowError, KeyError) as exc:
        return _fail(str(exc))

    return ParentFilteredExecutionProofDAGBinding(
        SCHEMA_VERSION,
        OUTPUT_STATUS,
        True,
        True,
        True,
        parent["parent_outcome"],
        execution["outcome"],
        parent["reduction_identity"],
        parent["child_result_identity"],
        parent["result_identity"],
        execution["closure_identity"],
        execution["result_lift_digest"],
        execution["proof_identity_digest"],
        execution["child_proof_identity_digest"],
        execution["child_degree"],
        True,
        False,
        binding_identity,
        (
            "rev2200 exact parent-filtered result and rev1400 execution proof-DAG replay to the same "
            "reduction and exact child-result identity; this certifies shared child-execution lineage only, "
            "not equality of their independently defined parent-result certificates"
        ),
    )


def replay_parent_filtered_execution_proof_dag_binding(
    certificate: ParentFilteredExecutionProofDAGBinding,
    parent_filtered_result: Any,
    execution_proof_dag_result: Any,
) -> bool:
    recomputed = certify_parent_filtered_execution_proof_dag_binding(
        parent_filtered_result,
        execution_proof_dag_result,
    )
    return recomputed.certified and recomputed == certificate
