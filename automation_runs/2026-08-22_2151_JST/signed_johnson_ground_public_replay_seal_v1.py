from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))

from s1_proof_identity_v1 import _freeze_group
from signed_johnson_ground_proof_dag_consumer_v1 import (
    SignedJohnsonGroundProofDAGConsumerResult,
    SignedJohnsonGroundProofIdentity,
    signed_johnson_ground_proof_dag_consumer,
)

_PROOF_STATUS = "certified_signed_johnson_ground_proof_dag"
_TERMINAL_STATUSES = frozenset({
    "exact_signed_johnson_ground_relation_coset",
    "exact_empty_signed_johnson_ground_relation",
})
_HEX = frozenset("0123456789abcdef")

@dataclass(frozen=True)
class SignedJohnsonGroundPublicReplaySeal:
    schema: str
    solver_identity: tuple[str, str, int]
    proof_status: str
    terminal_status: str
    root_n: int
    domain_size: int
    ground_size: int
    subset_size: int
    certified_signed_group_order: int
    signed_elements_checked: int
    recognition_search_nodes: int
    resource_identity: tuple[tuple[str, int], ...]
    proof_identity_sha256: str
    result_identity_sha256: str
    dag_status: str
    dag_unique_nodes: int
    dag_execution_occurrences: int
    dag_reused_occurrences: int
    dag_max_depth: int
    local_log2_cost_bound_hex: str
    dag_log2_work_bound_hex: str
    dag_allowed_log2_work_hex: str
    seal_sha256: str

@dataclass(frozen=True)
class SignedJohnsonGroundPublicReplaySealResult:
    status: str
    certified: bool
    seal: SignedJohnsonGroundPublicReplaySeal | None
    execution: SignedJohnsonGroundProofDAGConsumerResult | None
    reason: str

def _canonical(value):
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not isfinite(value):
            raise ValueError("non-finite value cannot enter public replay seal")
        return {"$float_hex": value.hex()}
    if is_dataclass(value):
        return {"$dataclass": value.__class__.__name__, "fields": [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]}
    if type(value) is tuple:
        return {"$tuple": [_canonical(item) for item in value]}
    if type(value) is list:
        return {"$list": [_canonical(item) for item in value]}
    if type(value) is dict:
        if not all(type(key) is str for key in value):
            raise ValueError("seal dictionaries require literal string keys")
        return {"$dict": [[key, _canonical(value[key])] for key in sorted(value)]}
    raise ValueError(f"opaque value cannot enter public replay seal: {type(value).__name__}")

def _digest(domain: str, value) -> str:
    encoded = json.dumps({"domain": domain, "value": _canonical(value)}, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()

def _valid_hex_digest(value: object) -> bool:
    return type(value) is str and len(value) == 64 and value == value.lower() and all(ch in _HEX for ch in value)

def _strict_positive_int(value: object) -> bool:
    return type(value) is int and value >= 1

def _strict_nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0

def _result_identity(execution: SignedJohnsonGroundProofDAGConsumerResult):
    proof = execution.proof
    if proof.status == "exact_empty_signed_johnson_ground_relation":
        if proof.coset is not None:
            raise ValueError("exact-empty signed Johnson result unexpectedly carries a coset")
        return ("exact_empty",)
    if proof.status != "exact_signed_johnson_ground_relation_coset" or proof.coset is None:
        raise ValueError("exact nonempty signed Johnson result lacks a right coset")
    return ("right_coset", tuple(proof.coset.representative), _freeze_group(proof.coset.subgroup))

def _seal_payload(identity: SignedJohnsonGroundProofIdentity, execution: SignedJohnsonGroundProofDAGConsumerResult, *, proof_identity_sha256: str, result_identity_sha256: str):
    dag = execution.dag_validation
    if dag is None:
        raise ValueError("certified rev295 execution lacks proof-DAG validation")
    return (
        "signed-johnson-ground-public-replay-seal-v1",
        ("signed_johnson_ground_proof_dag_consumer_v1", "signed_johnson_ground_public_replay_seal_v1", 3700),
        _PROOF_STATUS,
        str(identity.terminal_status),
        int(identity.root_n), int(identity.domain_size), int(identity.ground_size), int(identity.subset_size),
        int(identity.certified_signed_group_order), int(identity.signed_elements_checked), int(identity.recognition_search_nodes),
        tuple((str(name), int(value)) for name, value in identity.resource_identity),
        proof_identity_sha256, result_identity_sha256,
        str(dag.status), int(dag.unique_nodes), int(dag.execution_occurrences), int(dag.reused_occurrences), int(dag.max_depth),
        float(identity.local_log2_cost_bound).hex(), float(dag.log2_work_bound).hex(), float(dag.allowed_log2_work).hex(),
    )

def _build_seal_from_execution(execution: SignedJohnsonGroundProofDAGConsumerResult) -> SignedJohnsonGroundPublicReplaySeal:
    if not isinstance(execution, SignedJohnsonGroundProofDAGConsumerResult) or execution.status != _PROOF_STATUS:
        raise ValueError("only certified rev295 execution may receive a public replay seal")
    proof = execution.proof
    identity_validation = execution.identity_validation
    dag = execution.dag_validation
    if identity_validation is None or dag is None or not identity_validation.certified or not dag.certified:
        raise ValueError("rev295 identity or proof-DAG validation is not certified")
    identity = getattr(proof, "proof_identity", None)
    if not isinstance(identity, SignedJohnsonGroundProofIdentity) or not identity.replay_stable:
        raise ValueError("rev295 proof identity is absent, wrong-type, or unstable")
    if proof.status not in _TERMINAL_STATUSES or not proof.exact or not proof.canonical or not proof.terminal_certified:
        raise ValueError("rev295 proof is not an exact canonical terminal")
    if proof.children:
        raise ValueError("rev295 signed-ground terminal unexpectedly carries child proofs")
    if any(not isfinite(float(value)) or float(value) < 0.0 for value in (identity.local_log2_cost_bound, dag.log2_work_bound, dag.allowed_log2_work)):
        raise ValueError("rev295 accounting is non-finite or negative")
    proof_digest = _digest("rev295-signed-johnson-ground-proof-identity", identity)
    result_digest = _digest("rev295-signed-johnson-ground-result", _result_identity(execution))
    payload = _seal_payload(identity, execution, proof_identity_sha256=proof_digest, result_identity_sha256=result_digest)
    seal_digest = _digest("rev3700-signed-johnson-ground-public-replay-seal", payload)
    return SignedJohnsonGroundPublicReplaySeal(
        schema=payload[0], solver_identity=payload[1], proof_status=payload[2], terminal_status=payload[3], root_n=payload[4],
        domain_size=payload[5], ground_size=payload[6], subset_size=payload[7], certified_signed_group_order=payload[8],
        signed_elements_checked=payload[9], recognition_search_nodes=payload[10], resource_identity=payload[11],
        proof_identity_sha256=payload[12], result_identity_sha256=payload[13], dag_status=payload[14],
        dag_unique_nodes=payload[15], dag_execution_occurrences=payload[16], dag_reused_occurrences=payload[17], dag_max_depth=payload[18],
        local_log2_cost_bound_hex=payload[19], dag_log2_work_bound_hex=payload[20], dag_allowed_log2_work_hex=payload[21], seal_sha256=seal_digest,
    )

def _validate_seal_shape(seal: SignedJohnsonGroundPublicReplaySeal) -> str | None:
    if not isinstance(seal, SignedJohnsonGroundPublicReplaySeal):
        return "seal has wrong type"
    if seal.schema != "signed-johnson-ground-public-replay-seal-v1":
        return "public replay seal schema is unsupported"
    if seal.solver_identity != ("signed_johnson_ground_proof_dag_consumer_v1", "signed_johnson_ground_public_replay_seal_v1", 3700):
        return "public replay seal solver identity drifted"
    if seal.proof_status != _PROOF_STATUS or seal.terminal_status not in _TERMINAL_STATUSES:
        return "public replay seal exact status drifted"
    for name in ("root_n", "domain_size", "ground_size", "subset_size", "certified_signed_group_order", "signed_elements_checked", "dag_unique_nodes", "dag_execution_occurrences"):
        if not _strict_positive_int(getattr(seal, name)):
            return f"public replay seal {name} must be positive"
    for name in ("recognition_search_nodes", "dag_reused_occurrences", "dag_max_depth"):
        if not _strict_nonnegative_int(getattr(seal, name)):
            return f"public replay seal {name} must be nonnegative"
    if seal.root_n < seal.domain_size or seal.subset_size > seal.ground_size:
        return "public replay seal structural measure drifted"
    if seal.terminal_status == "exact_signed_johnson_ground_relation_coset":
        if seal.signed_elements_checked != 2 * seal.certified_signed_group_order:
            return "nonempty signed Johnson exact scan count drifted"
    elif seal.signed_elements_checked != seal.certified_signed_group_order:
        return "exact-empty signed Johnson exact scan count drifted"
    if type(seal.resource_identity) is not tuple or tuple(name for name, _ in seal.resource_identity) != ("group_order_poly_power", "max_group_order", "max_recognition_nodes"):
        return "public replay seal resource identity shape drifted"
    if any(type(item) is not tuple or len(item) != 2 or type(item[0]) is not str or not _strict_positive_int(item[1]) for item in seal.resource_identity):
        return "public replay seal resource identity is malformed"
    resources = dict(seal.resource_identity)
    if seal.certified_signed_group_order > min(resources["max_group_order"], seal.root_n ** resources["group_order_poly_power"]):
        return "public replay seal signed-group order gate drifted"
    for name in ("proof_identity_sha256", "result_identity_sha256", "seal_sha256"):
        if not _valid_hex_digest(getattr(seal, name)):
            return f"public replay seal {name} is malformed"
    if type(seal.dag_status) is not str or not seal.dag_status:
        return "public replay seal proof-DAG status is malformed"
    try:
        values = tuple(float.fromhex(value) for value in (seal.local_log2_cost_bound_hex, seal.dag_log2_work_bound_hex, seal.dag_allowed_log2_work_hex))
    except (TypeError, ValueError):
        return "public replay seal accounting hex is malformed"
    if any(not isfinite(value) or value < 0.0 for value in values):
        return "public replay seal accounting is non-finite or negative"
    payload = (seal.schema, seal.solver_identity, seal.proof_status, seal.terminal_status, seal.root_n, seal.domain_size, seal.ground_size, seal.subset_size, seal.certified_signed_group_order, seal.signed_elements_checked, seal.recognition_search_nodes, seal.resource_identity, seal.proof_identity_sha256, seal.result_identity_sha256, seal.dag_status, seal.dag_unique_nodes, seal.dag_execution_occurrences, seal.dag_reused_occurrences, seal.dag_max_depth, seal.local_log2_cost_bound_hex, seal.dag_log2_work_bound_hex, seal.dag_allowed_log2_work_hex)
    if _digest("rev3700-signed-johnson-ground-public-replay-seal", payload) != seal.seal_sha256:
        return "public replay seal digest does not match payload"
    return None

def build_signed_johnson_ground_public_replay_seal(group, source_values, target_values, *, root_n: int, group_order_poly_power: int = 2, max_group_order: int = 4096, max_recognition_nodes: int = 500000, quasipoly_power: int = 5, quasipoly_constant: float = 32768.0) -> SignedJohnsonGroundPublicReplaySealResult:
    execution = signed_johnson_ground_proof_dag_consumer(group, source_values, target_values, root_n=root_n, group_order_poly_power=group_order_poly_power, max_group_order=max_group_order, max_recognition_nodes=max_recognition_nodes, quasipoly_power=quasipoly_power, quasipoly_constant=quasipoly_constant)
    if execution.status != _PROOF_STATUS:
        return SignedJohnsonGroundPublicReplaySealResult("rev295_execution_not_certified", False, None, execution, execution.reason)
    try:
        seal = _build_seal_from_execution(execution)
    except (TypeError, ValueError) as exc:
        return SignedJohnsonGroundPublicReplaySealResult("rev295_execution_not_sealable", False, None, execution, str(exc))
    error = _validate_seal_shape(seal)
    if error is not None:
        return SignedJohnsonGroundPublicReplaySealResult("invalid_signed_johnson_ground_public_replay_seal", False, seal, execution, error)
    return SignedJohnsonGroundPublicReplaySealResult("certified_signed_johnson_ground_public_replay_seal", True, seal, execution, "rev295 exact signed-Johnson-ground execution is deterministically sealed for public replay")

def verify_signed_johnson_ground_public_replay_seal(seal, group, source_values, target_values, *, root_n: int, group_order_poly_power: int = 2, max_group_order: int = 4096, max_recognition_nodes: int = 500000, quasipoly_power: int = 5, quasipoly_constant: float = 32768.0) -> SignedJohnsonGroundPublicReplaySealResult:
    error = _validate_seal_shape(seal)
    if error is not None:
        return SignedJohnsonGroundPublicReplaySealResult("invalid_signed_johnson_ground_public_replay_seal", False, seal if isinstance(seal, SignedJohnsonGroundPublicReplaySeal) else None, None, error)
    rebuilt = build_signed_johnson_ground_public_replay_seal(group, source_values, target_values, root_n=root_n, group_order_poly_power=group_order_poly_power, max_group_order=max_group_order, max_recognition_nodes=max_recognition_nodes, quasipoly_power=quasipoly_power, quasipoly_constant=quasipoly_constant)
    if not rebuilt.certified or rebuilt.seal is None:
        return SignedJohnsonGroundPublicReplaySealResult("signed_johnson_ground_public_replay_failed", False, seal, rebuilt.execution, rebuilt.reason)
    if rebuilt.seal != seal:
        return SignedJohnsonGroundPublicReplaySealResult("signed_johnson_ground_public_replay_mismatch", False, seal, rebuilt.execution, "supplied seal differs from independent rev295 replay")
    return SignedJohnsonGroundPublicReplaySealResult("verified_signed_johnson_ground_public_replay_seal", True, seal, rebuilt.execution, "supplied seal exactly matches an independent rev295 execution replay")

__all__ = ["SignedJohnsonGroundPublicReplaySeal", "SignedJohnsonGroundPublicReplaySealResult", "build_signed_johnson_ground_public_replay_seal", "verify_signed_johnson_ground_public_replay_seal"]
