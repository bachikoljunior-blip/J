from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode

SCHEMA_VERSION = 1
REV1300_STATUS = "certified_corrected_soj_recursive_production_lineage_closure"
CHILD_NONEMPTY_STATUS = "exact_recursive_ground_coset"
CHILD_EMPTY_STATUS = "exact_empty_recursive_ground_coset"
LIFT_NONEMPTY_STATUS = "certified_exact_parent_johnson_coset_lift"
LIFT_EMPTY_STATUS = "certified_exact_empty_parent_johnson_result"
OUTPUT_NONEMPTY_STATUS = "certified_recursive_production_execution_parent_coset"
OUTPUT_EMPTY_STATUS = "certified_recursive_production_execution_parent_empty"
_BARE_SHA = re.compile(r"^[0-9a-f]{64}$")
_PREFIXED_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class RecursiveProductionExecutionProofIdentity:
    schema: str
    closure_identity: str
    result_lift_digest: str
    child_result_identity: str
    child_proof_identity: object
    parent_values_digest: str
    original_root_n: int
    replay_stable: bool = True


@dataclass(frozen=True)
class RecursiveProductionExecutionDAGResult:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    outcome_kind: str
    parent_action_degree: int
    child_ground_size: int
    reduction_identity: str
    closure_identity: str
    child_result_identity: str
    result_lift_digest: str
    proof_identity: RecursiveProductionExecutionProofIdentity | None
    proof: ProofCarryingCoset | None
    validation: ProofDAGValidation | None
    reason: str


def _fail(reason: str) -> RecursiveProductionExecutionDAGResult:
    return RecursiveProductionExecutionDAGResult(
        SCHEMA_VERSION,
        "recursive_production_execution_proof_dag_not_certified",
        False,
        False,
        False,
        "undetermined",
        0,
        0,
        "",
        "",
        "",
        "",
        None,
        None,
        None,
        reason,
    )


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _json_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
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


def _normalize_json(value: Any, path: str = "value") -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite")
        return value
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item, f"{path}[{i}]") for i, item in enumerate(value)]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{path} dictionary keys must be strings")
            normalized[key] = _normalize_json(item, f"{path}.{key}")
        return normalized
    raise ValueError(f"{path} is not replay-stable JSON data")


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _normalize_permutation(raw: Any, *, degree: int, name: str) -> tuple[int, ...]:
    seq = _sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong action degree")
    perm = tuple(_strict_int(image, f"{name}[{i}]", minimum=0) for i, image in enumerate(seq))
    if any(image >= degree for image in perm) or len(set(perm)) != degree:
        raise ValueError(f"{name} is not a permutation of 0..{degree - 1}")
    return perm


def _normalize_values(raw: Any, *, degree: int, name: str) -> tuple[Any, ...]:
    seq = _sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong parent action degree")
    return tuple(_normalize_json(value, f"{name}[{i}]") for i, value in enumerate(seq))


def _normalize_closure(certificate: Any) -> dict[str, Any]:
    if _field(certificate, "schema_version") != SCHEMA_VERSION:
        raise ValueError("rev1300 schema_version mismatch")
    if _field(certificate, "status") != REV1300_STATUS:
        raise ValueError("rev1300 status mismatch")
    for name in ("certified", "exact", "complete"):
        _literal_true(_field(certificate, name), f"rev1300.{name}")
    outcome = _field(certificate, "outcome_kind")
    if outcome not in {"nonempty", "exact_empty"}:
        raise ValueError("rev1300 outcome_kind is unsupported")
    parent = _strict_int(_field(certificate, "parent_action_degree"), "rev1300.parent_action_degree")
    child = _strict_int(_field(certificate, "child_ground_size"), "rev1300.child_ground_size")
    if child >= parent:
        raise ValueError("rev1300 must retain strict recursive shrink")
    bound = _finite(
        _field(certificate, "construction_multiplicative_cost_bound"),
        "rev1300.construction_multiplicative_cost_bound",
        minimum=1.0,
    )
    charge = _finite(
        _field(certificate, "charged_log2_reduction_cost"),
        "rev1300.charged_log2_reduction_cost",
    )
    if not bound.is_integer():
        raise ValueError("rev1300 construction cost bound must be integral")
    bound_int = int(bound)
    if bound_int & (bound_int - 1):
        raise ValueError("rev1300 construction cost bound must be a power of two")
    if charge != float(bound_int.bit_length() - 1):
        raise ValueError("rev1300 charged reduction cost must equal exact log2 construction bound")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": REV1300_STATUS,
        "main_commit_sha": _git_sha(_field(certificate, "main_commit_sha"), "rev1300.main_commit_sha"),
        "main_provenance_identity": _bare_sha(
            _field(certificate, "main_provenance_identity"), "rev1300.main_provenance_identity"
        ),
        "caller_binding_identity": _bare_sha(
            _field(certificate, "caller_binding_identity"), "rev1300.caller_binding_identity"
        ),
        "caller_replay_envelope_identity": _bare_sha(
            _field(certificate, "caller_replay_envelope_identity"), "rev1300.caller_replay_envelope_identity"
        ),
        "outcome_kind": outcome,
        "parent_action_degree": parent,
        "child_ground_size": child,
        "reduction_identity": _prefixed_sha(
            _field(certificate, "reduction_identity"), "rev1300.reduction_identity"
        ),
        "production_provenance_identity": _prefixed_sha(
            _field(certificate, "production_provenance_identity"), "rev1300.production_provenance_identity"
        ),
        "recursive_provenance_identity": _prefixed_sha(
            _field(certificate, "recursive_provenance_identity"), "rev1300.recursive_provenance_identity"
        ),
        "result_lift_digest": _prefixed_sha(
            _field(certificate, "result_lift_digest"), "rev1300.result_lift_digest"
        ),
        "accounting_binding_digest": _prefixed_sha(
            _field(certificate, "accounting_binding_digest"), "rev1300.accounting_binding_digest"
        ),
        "child_result_identity": _prefixed_sha(
            _field(certificate, "child_result_identity"), "rev1300.child_result_identity"
        ),
        "coherence_identity": _prefixed_sha(
            _field(certificate, "coherence_identity"), "rev1300.coherence_identity"
        ),
        "construction_cost_binding_identity": _prefixed_sha(
            _field(certificate, "construction_cost_binding_identity"),
            "rev1300.construction_cost_binding_identity",
        ),
        "construction_multiplicative_cost_bound": bound,
        "charged_log2_reduction_cost": charge,
        "total_cost_binding_identity": _prefixed_sha(
            _field(certificate, "total_cost_binding_identity"), "rev1300.total_cost_binding_identity"
        ),
        "post_replay_envelope_identity": _prefixed_sha(
            _field(certificate, "post_replay_envelope_identity"), "rev1300.post_replay_envelope_identity"
        ),
        "main_post_replay_seal_identity": _prefixed_sha(
            _field(certificate, "main_post_replay_seal_identity"), "rev1300.main_post_replay_seal_identity"
        ),
    }
    closure_identity = _prefixed_sha(_field(certificate, "closure_identity"), "rev1300.closure_identity")
    if _canonical_hash(payload) != closure_identity:
        raise ValueError("rev1300 closure_identity replay failed")
    return payload | {"closure_identity": closure_identity}


def _normalize_child_result(
    evidence: Any, *, child_degree: int, reduction_identity: str, expected_outcome: str
) -> dict[str, Any]:
    if _field(evidence, "schema_version") != SCHEMA_VERSION:
        raise ValueError("rev293 child-result schema_version mismatch")
    expected_status = CHILD_NONEMPTY_STATUS if expected_outcome == "nonempty" else CHILD_EMPTY_STATUS
    if _field(evidence, "status") != expected_status:
        raise ValueError("rev293 child-result status disagrees with rev1300 outcome")
    for name in ("exact", "complete", "canonical", "ambient_membership_certified"):
        _literal_true(_field(evidence, name), f"child_result.{name}")
    if _strict_int(_field(evidence, "action_degree"), "child_result.action_degree") != child_degree:
        raise ValueError("child-result action degree differs from rev1300 child ground")
    if _field(evidence, "reduction_identity") != reduction_identity:
        raise ValueError("child-result reduction identity differs from rev1300")

    representative = _field(evidence, "representative")
    raw_generators = _field(evidence, "stabilizer_generators")
    if expected_outcome == "exact_empty":
        if representative is not None or tuple(raw_generators) != ():
            raise ValueError("exact-empty child result may not carry coset data")
        normalized_rep = None
        generators: tuple[tuple[int, ...], ...] = ()
    else:
        if representative is None:
            raise ValueError("nonempty child result requires a representative")
        normalized_rep = _normalize_permutation(representative, degree=child_degree, name="child_result.representative")
        seq = _sequence(raw_generators, "child_result.stabilizer_generators")
        generators = tuple(
            _normalize_permutation(raw, degree=child_degree, name=f"child_result.stabilizer_generators[{i}]")
            for i, raw in enumerate(seq)
        )
        if generators != tuple(sorted(set(generators))):
            raise ValueError("child-result stabilizer generators must be unique and canonical")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": expected_status,
        "exact": True,
        "complete": True,
        "canonical": True,
        "ambient_membership_certified": True,
        "action_degree": child_degree,
        "reduction_identity": reduction_identity,
        "representative": normalized_rep,
        "stabilizer_generators": generators,
    }
    observed = _prefixed_sha(_field(evidence, "result_identity"), "child_result.result_identity")
    if _json_hash(payload) != observed:
        raise ValueError("rev293 child result_identity replay failed")
    return payload | {"result_identity": observed}


def _normalize_lift(
    certificate: Any,
    *,
    closure: Mapping[str, Any],
    child: Mapping[str, Any],
    parent_source_values: Sequence[Any],
    parent_target_values: Sequence[Any],
) -> tuple[dict[str, Any], tuple[Any, ...], tuple[Any, ...], str]:
    if _field(certificate, "schema_version") != SCHEMA_VERSION:
        raise ValueError("rev293 result-lift schema_version mismatch")
    expected_status = LIFT_NONEMPTY_STATUS if closure["outcome_kind"] == "nonempty" else LIFT_EMPTY_STATUS
    if _field(certificate, "status") != expected_status:
        raise ValueError("rev293 result-lift status disagrees with rev1300 outcome")
    for name in ("certified", "exact", "complete"):
        _literal_true(_field(certificate, name), f"result_lift.{name}")
    if _strict_int(_field(certificate, "parent_action_degree"), "result_lift.parent_action_degree") != closure["parent_action_degree"]:
        raise ValueError("result-lift parent degree differs from rev1300")
    if _strict_int(_field(certificate, "child_ground_size"), "result_lift.child_ground_size") != closure["child_ground_size"]:
        raise ValueError("result-lift child ground differs from rev1300")
    if _field(certificate, "reduction_identity") != closure["reduction_identity"]:
        raise ValueError("result-lift reduction identity differs from rev1300")
    if _field(certificate, "child_result_identity") != child["result_identity"]:
        raise ValueError("result-lift child result identity differs from replayed child result")

    parent_degree = closure["parent_action_degree"]
    source = _normalize_values(parent_source_values, degree=parent_degree, name="parent_source_values")
    target = _normalize_values(parent_target_values, degree=parent_degree, name="parent_target_values")
    parent_values_digest = _json_hash({"source": source, "target": target})

    representative = _field(certificate, "parent_representative")
    raw_generators = _field(certificate, "parent_stabilizer_generators")
    if closure["outcome_kind"] == "exact_empty":
        if representative is not None or tuple(raw_generators) != ():
            raise ValueError("exact-empty parent lift may not carry coset data")
        parent_rep = None
        parent_gens: tuple[tuple[int, ...], ...] = ()
        transcript_payload = {
            "schema_version": SCHEMA_VERSION,
            "status": expected_status,
            "reduction_identity": closure["reduction_identity"],
            "child_result_identity": child["result_identity"],
            "parent_values_digest": parent_values_digest,
            "parent_action_degree": parent_degree,
            "child_ground_size": closure["child_ground_size"],
        }
    else:
        if representative is None:
            raise ValueError("nonempty parent lift requires a representative")
        parent_rep = _normalize_permutation(representative, degree=parent_degree, name="result_lift.parent_representative")
        seq = _sequence(raw_generators, "result_lift.parent_stabilizer_generators")
        parent_gens = tuple(
            _normalize_permutation(raw, degree=parent_degree, name=f"result_lift.parent_stabilizer_generators[{i}]")
            for i, raw in enumerate(seq)
        )
        transcript_payload = {
            "schema_version": SCHEMA_VERSION,
            "status": expected_status,
            "reduction_identity": closure["reduction_identity"],
            "child_result_identity": child["result_identity"],
            "parent_values_digest": parent_values_digest,
            "parent_action_degree": parent_degree,
            "child_ground_size": closure["child_ground_size"],
            "parent_representative": parent_rep,
            "parent_stabilizer_generators": parent_gens,
        }
    observed = _prefixed_sha(_field(certificate, "transcript_digest"), "result_lift.transcript_digest")
    if _json_hash(transcript_payload) != observed:
        raise ValueError("rev293 result-lift transcript replay failed")
    if observed != closure["result_lift_digest"]:
        raise ValueError("rev293 result-lift transcript differs from rev1300 result_lift_digest")
    return (
        transcript_payload | {"transcript_digest": observed},
        source,
        target,
        parent_values_digest,
    )


def _transports(source: tuple[Any, ...], target: tuple[Any, ...], permutation: tuple[int, ...]) -> bool:
    return all(source[index] == target[permutation[index]] for index in range(len(source)))


def _stabilizes(values: tuple[Any, ...], permutation: tuple[int, ...]) -> bool:
    return all(values[index] == values[permutation[index]] for index in range(len(values)))


def _group_from_generators(generators: tuple[tuple[int, ...], ...], degree: int):
    return schreier_stabilizer_chain(generators or (identity(degree),))


def _same_coset(actual: RightCoset, representative: tuple[int, ...], generators: tuple[tuple[int, ...], ...]) -> bool:
    degree = len(representative)
    if actual.subgroup.degree != degree or len(actual.representative) != degree:
        return False
    expected_group = _group_from_generators(generators, degree)
    if actual.subgroup.order != expected_group.order:
        return False
    actual_generators = tuple(getattr(actual.subgroup, "generators", ()))
    if any(not actual.subgroup.contains(generator) for generator in generators):
        return False
    if any(not expected_group.contains(generator) for generator in actual_generators):
        return False
    expected = RightCoset(expected_group, representative)
    return bool(actual.contains(representative) and expected.contains(actual.representative))


def certify_recursive_production_execution_proof_dag(
    lineage_closure: Any,
    child_result_evidence: Any,
    result_lift_certificate: Any,
    child_proof: ProofCarryingCoset,
    *,
    parent_source_values: Sequence[Any],
    parent_target_values: Sequence[Any],
    original_root_n: int,
    external_log2_cost_bound: float = 0.0,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> RecursiveProductionExecutionDAGResult:
    """Bind one concrete recursive child execution to rev1300/rev293 public evidence.

    This adapter does not run recursive String Isomorphism. It accepts only an
    already exact/cost-certified child proof whose replay-stable identity and
    exact coset semantics agree with the public rev293 child-result snapshot. It
    independently replays the rev1300 lineage closure and rev293 transcript,
    reconstructs the parent outcome, then charges the single recursive edge
    through the main-integrated recurrence/proof-DAG validator.
    """
    try:
        closure = _normalize_closure(lineage_closure)
        child = _normalize_child_result(
            child_result_evidence,
            child_degree=closure["child_ground_size"],
            reduction_identity=closure["reduction_identity"],
            expected_outcome=closure["outcome_kind"],
        )
        if child["result_identity"] != closure["child_result_identity"]:
            raise ValueError("replayed child result identity differs from rev1300")
        lift, source, target, parent_values_digest = _normalize_lift(
            result_lift_certificate,
            closure=closure,
            child=child,
            parent_source_values=parent_source_values,
            parent_target_values=parent_target_values,
        )
        root_n = _strict_int(original_root_n, "original_root_n")
        if closure["parent_action_degree"] > root_n:
            raise ValueError("original_root_n must dominate the parent action degree")
        external = _finite(external_log2_cost_bound, "external_log2_cost_bound")
    except (TypeError, ValueError, OverflowError) as exc:
        return _fail(str(exc))

    if not isinstance(child_proof, ProofCarryingCoset):
        return _fail("child_proof must be a concrete ProofCarryingCoset execution")
    if child_proof.root_n != root_n:
        return _fail("child proof root_n differs from the requested original root")
    if child_proof.domain_size != closure["child_ground_size"]:
        return _fail("child proof domain differs from the certified recursive ground")
    if type(child_proof.exact) is not bool or not child_proof.exact:
        return _fail("child proof is not exact")
    if type(child_proof.canonical) is not bool or not child_proof.canonical:
        return _fail("child proof is not canonical")
    if type(child_proof.local_cost_certified) is not bool or not child_proof.local_cost_certified:
        return _fail("child proof local execution cost is not certified")
    if child_proof.accounting.n != root_n or child_proof.accounting.m != closure["child_ground_size"]:
        return _fail("child proof accounting measures differ from the recursive ground")
    child_identity = getattr(child_proof, "proof_identity", None)
    if child_identity is None or getattr(child_identity, "replay_stable", False) is not True:
        return _fail("child proof requires a replay-stable attached proof identity")
    try:
        hash(child_identity)
    except TypeError:
        return _fail("child proof identity must be immutable and hashable")

    if closure["outcome_kind"] == "exact_empty":
        if child_proof.coset is not None:
            return _fail("exact-empty child evidence disagrees with nonempty child proof")
        parent_coset = None
    else:
        if child_proof.coset is None:
            return _fail("nonempty child evidence disagrees with empty child proof")
        assert child["representative"] is not None
        if not _same_coset(child_proof.coset, child["representative"], child["stabilizer_generators"]):
            return _fail("concrete child proof coset differs from replayed rev293 child evidence")
        parent_rep = lift["parent_representative"]
        parent_gens = lift["parent_stabilizer_generators"]
        assert parent_rep is not None
        if not _transports(source, target, parent_rep):
            return _fail("replayed parent representative does not transport source to target")
        if any(not _stabilizes(target, generator) for generator in parent_gens):
            return _fail("a replayed parent stabilizer generator does not stabilize the target")
        parent_group = _group_from_generators(parent_gens, closure["parent_action_degree"])
        parent_coset = RightCoset(parent_group, parent_rep)

    if closure["child_ground_size"] > 0.9 * closure["parent_action_degree"] + 1e-12:
        return _fail("recursive production edge does not satisfy recurrence-v4 aux_shrink progress")

    proof_identity = RecursiveProductionExecutionProofIdentity(
        "corrected-soj-recursive-production-execution-proof-dag-v1",
        closure["closure_identity"],
        closure["result_lift_digest"],
        closure["child_result_identity"],
        child_identity,
        parent_values_digest,
        root_n,
        True,
    )
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=closure["parent_action_degree"],
        operation_kind="aux_shrink",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=closure["charged_log2_reduction_cost"],
        children=(AccountingChild(child_proof.accounting, 1),),
        terminal_certified=False,
        reason=(
            "rev1400: one replayed larger-ground Johnson recursive edge; construction work is charged exactly once before the already exact child execution"
        ),
    )
    status = OUTPUT_NONEMPTY_STATUS if parent_coset is not None else OUTPUT_EMPTY_STATUS
    root_proof = ProofCarryingCoset(
        status,
        parent_coset,
        "aux_shrink",
        root_n,
        closure["parent_action_degree"],
        True,
        True,
        True,
        closure["charged_log2_reduction_cost"],
        False,
        (child_proof,),
        accounting,
        0,
        "public lineage/result-lift replay agrees with one concrete exact recursive child execution",
        proof_identity,
    )
    validation = validate_execution_proof_dag(
        root_proof,
        original_root_n=root_n,
        external_log2_cost_bound=external,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not validation.certified:
        return RecursiveProductionExecutionDAGResult(
            SCHEMA_VERSION,
            "recursive_production_execution_proof_dag_not_certified",
            False,
            False,
            False,
            closure["outcome_kind"],
            closure["parent_action_degree"],
            closure["child_ground_size"],
            closure["reduction_identity"],
            closure["closure_identity"],
            closure["child_result_identity"],
            closure["result_lift_digest"],
            proof_identity,
            root_proof,
            validation,
            "shared execution proof-DAG rejected the composed recursive execution: " + validation.reason,
        )
    return RecursiveProductionExecutionDAGResult(
        SCHEMA_VERSION,
        status,
        True,
        True,
        True,
        closure["outcome_kind"],
        closure["parent_action_degree"],
        closure["child_ground_size"],
        closure["reduction_identity"],
        closure["closure_identity"],
        closure["child_result_identity"],
        closure["result_lift_digest"],
        proof_identity,
        root_proof,
        validation,
        "the concrete recursive child execution, exact parent lift, strict recurrence progress, and conservative proof-DAG occurrence charge all replay consistently",
    )


def replay_recursive_production_execution_proof_dag(
    result: RecursiveProductionExecutionDAGResult,
    *args: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(result, RecursiveProductionExecutionDAGResult) or not result.certified:
        return False
    replay = certify_recursive_production_execution_proof_dag(*args, **kwargs)
    return bool(replay.certified and replay == result)


__all__ = [
    "RecursiveProductionExecutionProofIdentity",
    "RecursiveProductionExecutionDAGResult",
    "certify_recursive_production_execution_proof_dag",
    "replay_recursive_production_execution_proof_dag",
]
