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

from proof_carrying_small_order_production_admission_v1 import ProductionAdmissionCaps
from small_order_production_proof_dag_consumer_v1 import (
    SmallOrderProductionProofDAGConsumerResult,
    SmallOrderProductionProofIdentity,
    small_order_production_proof_dag_consumer,
)


_EXACT_NONEMPTY = "exact_small_order_group_coset"
_EXACT_EMPTY = "exact_empty_small_order_group"
_HEX = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class SmallOrderPublicReplaySeal:
    schema: str
    solver_identity: tuple[str, str, int]
    outcome: str
    proof_status: str
    root_n: int
    domain_size: int
    certified_group_order: int
    claimed_match_count: int
    certificate_sha256: str
    proof_identity_sha256: str
    replay_identity_sha256: str
    dag_status: str
    dag_unique_nodes: int
    dag_execution_occurrences: int
    dag_reused_occurrences: int
    dag_max_depth: int
    dag_log2_work_bound_hex: str
    dag_allowed_log2_work_hex: str
    external_log2_cost_bound_hex: str
    seal_sha256: str


@dataclass(frozen=True)
class SmallOrderPublicReplaySealResult:
    status: str
    certified: bool
    seal: SmallOrderPublicReplaySeal | None
    execution: SmallOrderProductionProofDAGConsumerResult | None
    reason: str


def _canonical(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("non-finite values cannot enter a public replay seal")
        return {"$float_hex": value.hex()}
    if is_dataclass(value):
        return {
            "$dataclass": value.__class__.__name__,
            "fields": [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)],
        }
    if isinstance(value, tuple):
        return {"$tuple": [_canonical(item) for item in value]}
    if isinstance(value, list):
        return {"$list": [_canonical(item) for item in value]}
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("public replay seal dictionaries require string keys")
        return {"$dict": [[key, _canonical(value[key])] for key in sorted(value)]}
    raise ValueError(f"opaque value cannot enter a public replay seal: {type(value).__name__}")


def _digest(domain: str, value) -> str:
    payload = {
        "domain": str(domain),
        "value": _canonical(value),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(ch in _HEX for ch in value)
    )


def _seal_payload(
    *,
    identity: SmallOrderProductionProofIdentity,
    execution: SmallOrderProductionProofDAGConsumerResult,
    outcome: str,
    proof_identity_sha256: str,
    replay_identity_sha256: str,
):
    dag = execution.dag_validation
    if dag is None:
        raise ValueError("certified rev620 execution lacks proof-DAG validation")
    return (
        "small-order-production-public-replay-seal-v1",
        ("small_order_production_proof_dag_consumer_v1", "small_order_public_replay_seal_v1", 3200),
        outcome,
        str(identity.producer_status),
        int(identity.root_n),
        int(identity.domain_size),
        int(identity.certified_group_order),
        int(identity.claimed_match_count),
        str(identity.certificate_sha256),
        proof_identity_sha256,
        replay_identity_sha256,
        str(dag.status),
        int(dag.unique_nodes),
        int(dag.execution_occurrences),
        int(dag.reused_occurrences),
        int(dag.max_depth),
        float(dag.log2_work_bound).hex(),
        float(dag.allowed_log2_work).hex(),
        float(identity.external_log2_cost_bound).hex(),
    )


def _build_seal_from_execution(
    execution: SmallOrderProductionProofDAGConsumerResult,
) -> SmallOrderPublicReplaySeal:
    if not isinstance(execution, SmallOrderProductionProofDAGConsumerResult) or not execution.certified:
        raise ValueError("only a certified rev620 execution may receive a public replay seal")
    proof = execution.proof
    admission = execution.admission
    identity_validation = execution.identity_validation
    dag = execution.dag_validation
    if proof is None or admission is None or identity_validation is None or dag is None:
        raise ValueError("certified rev620 execution is structurally incomplete")
    if not identity_validation.certified or not dag.certified:
        raise ValueError("rev620 identity or proof-DAG validation is not certified")
    identity = getattr(proof, "proof_identity", None)
    if not isinstance(identity, SmallOrderProductionProofIdentity) or not identity.replay_stable:
        raise ValueError("rev620 proof identity is absent, wrong-type, or not replay-stable")
    if proof.status == _EXACT_NONEMPTY:
        outcome = "exact_nonempty"
        if proof.coset is None or identity.claimed_match_count < 1:
            raise ValueError("rev620 nonempty outcome lacks its exact transporter evidence")
    elif proof.status == _EXACT_EMPTY:
        outcome = "exact_empty"
        if proof.coset is not None or identity.claimed_match_count != 0:
            raise ValueError("rev620 exact-empty outcome carries inconsistent transporter evidence")
    else:
        raise ValueError("rev620 public replay seals require an exact nonempty or exact-empty terminal")
    if identity.producer_status != proof.status:
        raise ValueError("rev620 proof status drifted from its frozen production identity")
    if identity.certificate_sha256 != admission.certificate_sha256 or not _valid_sha256(identity.certificate_sha256):
        raise ValueError("rev620 certificate digest is malformed or inconsistent")
    if not isfinite(float(identity.external_log2_cost_bound)) or identity.external_log2_cost_bound < 0.0:
        raise ValueError("rev620 external replay charge is not finite and nonnegative")
    if not isfinite(float(dag.log2_work_bound)) or not isfinite(float(dag.allowed_log2_work)):
        raise ValueError("rev620 proof-DAG accounting contains non-finite bounds")

    proof_digest = _digest("rev620-small-order-production-proof-identity", identity)
    replay_digest = _digest("rev620-small-order-production-replay-identity", identity.replay_identity)
    payload = _seal_payload(
        identity=identity,
        execution=execution,
        outcome=outcome,
        proof_identity_sha256=proof_digest,
        replay_identity_sha256=replay_digest,
    )
    seal_digest = _digest("rev3200-small-order-public-replay-seal", payload)
    return SmallOrderPublicReplaySeal(
        schema=payload[0],
        solver_identity=payload[1],
        outcome=payload[2],
        proof_status=payload[3],
        root_n=payload[4],
        domain_size=payload[5],
        certified_group_order=payload[6],
        claimed_match_count=payload[7],
        certificate_sha256=payload[8],
        proof_identity_sha256=payload[9],
        replay_identity_sha256=payload[10],
        dag_status=payload[11],
        dag_unique_nodes=payload[12],
        dag_execution_occurrences=payload[13],
        dag_reused_occurrences=payload[14],
        dag_max_depth=payload[15],
        dag_log2_work_bound_hex=payload[16],
        dag_allowed_log2_work_hex=payload[17],
        external_log2_cost_bound_hex=payload[18],
        seal_sha256=seal_digest,
    )


def _validate_seal_shape(seal: SmallOrderPublicReplaySeal) -> str | None:
    if not isinstance(seal, SmallOrderPublicReplaySeal):
        return "seal is not a SmallOrderPublicReplaySeal"
    if seal.schema != "small-order-production-public-replay-seal-v1":
        return "public replay seal schema is unsupported"
    if seal.solver_identity != (
        "small_order_production_proof_dag_consumer_v1",
        "small_order_public_replay_seal_v1",
        3200,
    ):
        return "public replay seal solver identity drifted"
    if seal.outcome not in {"exact_nonempty", "exact_empty"}:
        return "public replay seal outcome is not exact"
    if seal.proof_status not in {_EXACT_NONEMPTY, _EXACT_EMPTY}:
        return "public replay seal proof status is not exact"
    if (seal.outcome == "exact_nonempty") != (seal.proof_status == _EXACT_NONEMPTY):
        return "public replay seal outcome/status pairing is inconsistent"
    for name in (
        "root_n",
        "domain_size",
        "certified_group_order",
        "dag_unique_nodes",
        "dag_execution_occurrences",
    ):
        value = getattr(seal, name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            return f"public replay seal {name} must be a positive integer"
    for name in ("claimed_match_count", "dag_reused_occurrences", "dag_max_depth"):
        value = getattr(seal, name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return f"public replay seal {name} must be a nonnegative integer"
    if seal.root_n < seal.domain_size:
        return "public replay seal root does not dominate the executed domain"
    if seal.outcome == "exact_empty" and seal.claimed_match_count != 0:
        return "public replay seal exact-empty outcome has nonzero matches"
    if seal.outcome == "exact_nonempty" and seal.claimed_match_count < 1:
        return "public replay seal nonempty outcome has no matches"
    for name in (
        "certificate_sha256",
        "proof_identity_sha256",
        "replay_identity_sha256",
        "seal_sha256",
    ):
        if not _valid_sha256(getattr(seal, name)):
            return f"public replay seal {name} is malformed"
    try:
        for value in (
            seal.dag_log2_work_bound_hex,
            seal.dag_allowed_log2_work_hex,
            seal.external_log2_cost_bound_hex,
        ):
            decoded = float.fromhex(value)
            if not isfinite(decoded) or decoded < 0.0:
                return "public replay seal accounting bound is not finite and nonnegative"
    except (TypeError, ValueError):
        return "public replay seal accounting hex is malformed"
    payload = (
        seal.schema,
        seal.solver_identity,
        seal.outcome,
        seal.proof_status,
        seal.root_n,
        seal.domain_size,
        seal.certified_group_order,
        seal.claimed_match_count,
        seal.certificate_sha256,
        seal.proof_identity_sha256,
        seal.replay_identity_sha256,
        seal.dag_status,
        seal.dag_unique_nodes,
        seal.dag_execution_occurrences,
        seal.dag_reused_occurrences,
        seal.dag_max_depth,
        seal.dag_log2_work_bound_hex,
        seal.dag_allowed_log2_work_hex,
        seal.external_log2_cost_bound_hex,
    )
    if _digest("rev3200-small-order-public-replay-seal", payload) != seal.seal_sha256:
        return "public replay seal digest does not match its payload"
    return None


def build_small_order_public_replay_seal(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    group_order_poly_power: int = 2,
    caps: ProductionAdmissionCaps = ProductionAdmissionCaps(),
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> SmallOrderPublicReplaySealResult:
    execution = small_order_production_proof_dag_consumer(
        group,
        source_values,
        target_values,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        caps=caps,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not execution.certified:
        return SmallOrderPublicReplaySealResult(
            "rev620_execution_not_certified",
            False,
            None,
            execution,
            execution.reason,
        )
    try:
        seal = _build_seal_from_execution(execution)
    except (TypeError, ValueError) as exc:
        return SmallOrderPublicReplaySealResult(
            "rev620_execution_not_sealable",
            False,
            None,
            execution,
            str(exc),
        )
    shape_error = _validate_seal_shape(seal)
    if shape_error is not None:
        return SmallOrderPublicReplaySealResult(
            "invalid_small_order_public_replay_seal",
            False,
            seal,
            execution,
            shape_error,
        )
    return SmallOrderPublicReplaySealResult(
        "certified_small_order_public_replay_seal",
        True,
        seal,
        execution,
        "the main-integrated rev620 exact small-order production proof-DAG is named by one domain-separated deterministic replay seal",
    )


def verify_small_order_public_replay_seal(
    group,
    source_values,
    target_values,
    seal: SmallOrderPublicReplaySeal,
    *,
    root_n: int | None = None,
    group_order_poly_power: int = 2,
    caps: ProductionAdmissionCaps = ProductionAdmissionCaps(),
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> SmallOrderPublicReplaySealResult:
    shape_error = _validate_seal_shape(seal)
    if shape_error is not None:
        return SmallOrderPublicReplaySealResult(
            "invalid_small_order_public_replay_seal",
            False,
            seal if isinstance(seal, SmallOrderPublicReplaySeal) else None,
            None,
            shape_error,
        )
    replayed = build_small_order_public_replay_seal(
        group,
        source_values,
        target_values,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        caps=caps,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not replayed.certified or replayed.seal is None:
        return SmallOrderPublicReplaySealResult(
            "small_order_public_replay_execution_failed",
            False,
            seal,
            replayed.execution,
            replayed.reason,
        )
    if replayed.seal != seal:
        return SmallOrderPublicReplaySealResult(
            "small_order_public_replay_seal_mismatch",
            False,
            seal,
            replayed.execution,
            "independent rev620 re-execution produced a different public replay seal",
        )
    return SmallOrderPublicReplaySealResult(
        "verified_small_order_public_replay_seal",
        True,
        seal,
        replayed.execution,
        "independent rev620 re-execution reproduced the exact public replay seal",
    )


__all__ = [
    "ProductionAdmissionCaps",
    "SmallOrderPublicReplaySeal",
    "SmallOrderPublicReplaySealResult",
    "build_small_order_public_replay_seal",
    "verify_small_order_public_replay_seal",
]
