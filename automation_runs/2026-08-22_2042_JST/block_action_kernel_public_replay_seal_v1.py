from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REV950 = HERE.parent / "2026-08-22_1453_JST"
LEGACY = HERE.parent / "2026-08-19_0851_JST"
for path in (REV950, LEGACY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from block_action_kernel_proof_dag_consumer_v1 import (
    BlockActionKernelProofDAGConsumerResult,
    BlockActionKernelProofIdentity,
    block_action_kernel_proof_dag_consumer,
)


_PROOF_STATUS = "exact_block_action_kernel_factorization_proof_terminal"
_HEX = frozenset("0123456789abcdef")
_WORK_KEYS = (
    "estimated_schreier_work_units",
    "work_cap",
    "source_sift_levels",
    "target_sift_levels",
)
_ORDER_KEYS = (
    "source_group_order",
    "target_group_order",
    "quotient_image_order",
    "source_kernel_order",
    "target_kernel_order",
)


@dataclass(frozen=True)
class BlockActionKernelPublicReplaySeal:
    schema: str
    solver_identity: tuple[str, str, int]
    proof_status: str
    root_n: int
    domain_degree: int
    block_count: int
    generator_count: int
    provenance_digest: str
    factorization_digest: str
    proof_identity_sha256: str
    source_kernel_generators_sha256: str
    target_kernel_generators_sha256: str
    work_identity: tuple[tuple[str, int], ...]
    order_identity: tuple[tuple[str, int], ...]
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
class BlockActionKernelPublicReplaySealResult:
    status: str
    certified: bool
    seal: BlockActionKernelPublicReplaySeal | None
    execution: BlockActionKernelProofDAGConsumerResult | None
    reason: str


def _canonical(value):
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not isfinite(value):
            raise ValueError("non-finite values cannot enter a public replay seal")
        return {"$float_hex": value.hex()}
    if is_dataclass(value):
        return {
            "$dataclass": value.__class__.__name__,
            "fields": [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)],
        }
    if type(value) is tuple:
        return {"$tuple": [_canonical(item) for item in value]}
    if type(value) is list:
        return {"$list": [_canonical(item) for item in value]}
    if type(value) is dict:
        if not all(type(key) is str for key in value):
            raise ValueError("public replay seal dictionaries require literal string keys")
        return {"$dict": [[key, _canonical(value[key])] for key in sorted(value)]}
    raise ValueError(f"opaque value cannot enter a public replay seal: {type(value).__name__}")


def _digest(domain: str, value) -> str:
    payload = {"domain": str(domain), "value": _canonical(value)}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def _valid_hex_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(ch in _HEX for ch in value)
    )


def _valid_prefixed_digest(value: object) -> bool:
    return type(value) is str and value.startswith("sha256:") and _valid_hex_digest(value[7:])


def _strict_nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _strict_positive_int(value: object) -> bool:
    return type(value) is int and value >= 1


def _seal_payload(
    identity: BlockActionKernelProofIdentity,
    execution: BlockActionKernelProofDAGConsumerResult,
    *,
    proof_identity_sha256: str,
    source_kernel_generators_sha256: str,
    target_kernel_generators_sha256: str,
):
    dag = execution.dag_validation
    if dag is None:
        raise ValueError("certified rev950 execution lacks proof-DAG validation")
    return (
        "block-action-kernel-public-replay-seal-v1",
        ("block_action_kernel_proof_dag_consumer_v1", "block_action_kernel_public_replay_seal_v1", 3300),
        _PROOF_STATUS,
        int(identity.root_n),
        int(identity.domain_degree),
        int(identity.block_count),
        int(identity.generator_count),
        str(identity.provenance_digest),
        str(identity.factorization_digest),
        proof_identity_sha256,
        source_kernel_generators_sha256,
        target_kernel_generators_sha256,
        tuple((str(name), int(value)) for name, value in identity.work_identity),
        tuple((str(name), int(value)) for name, value in identity.order_identity),
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
    execution: BlockActionKernelProofDAGConsumerResult,
) -> BlockActionKernelPublicReplaySeal:
    if not isinstance(execution, BlockActionKernelProofDAGConsumerResult) or not execution.certified:
        raise ValueError("only a certified rev950 execution may receive a public replay seal")
    proof = execution.proof
    identity_validation = execution.identity_validation
    dag = execution.dag_validation
    if proof is None or identity_validation is None or dag is None:
        raise ValueError("certified rev950 execution is structurally incomplete")
    if not identity_validation.certified or not dag.certified:
        raise ValueError("rev950 identity or proof-DAG validation is not certified")
    identity = getattr(proof, "proof_identity", None)
    if not isinstance(identity, BlockActionKernelProofIdentity) or not identity.replay_stable:
        raise ValueError("rev950 proof identity is absent, wrong-type, or not replay-stable")
    if proof.status != _PROOF_STATUS or not proof.exact or not proof.canonical or not proof.terminal_certified:
        raise ValueError("rev950 proof is not the exact canonical kernel-factorization terminal")
    if proof.coset is not None or proof.children:
        raise ValueError("rev950 structural kernel-factorization terminal unexpectedly carries a coset or child")
    if not _valid_prefixed_digest(identity.provenance_digest) or not _valid_prefixed_digest(identity.factorization_digest):
        raise ValueError("rev950 provenance or factorization digest is malformed")
    if not isfinite(float(identity.external_log2_cost_bound)) or identity.external_log2_cost_bound < 0.0:
        raise ValueError("rev950 external replay charge is not finite and nonnegative")
    if not isfinite(float(dag.log2_work_bound)) or not isfinite(float(dag.allowed_log2_work)):
        raise ValueError("rev950 proof-DAG accounting contains non-finite bounds")

    proof_digest = _digest("rev950-block-action-kernel-proof-identity", identity)
    source_kernel_digest = _digest(
        "rev950-source-kernel-generator-family",
        identity.source_kernel_generators,
    )
    target_kernel_digest = _digest(
        "rev950-target-kernel-generator-family",
        identity.target_kernel_generators,
    )
    payload = _seal_payload(
        identity,
        execution,
        proof_identity_sha256=proof_digest,
        source_kernel_generators_sha256=source_kernel_digest,
        target_kernel_generators_sha256=target_kernel_digest,
    )
    seal_digest = _digest("rev3300-block-action-kernel-public-replay-seal", payload)
    return BlockActionKernelPublicReplaySeal(
        schema=payload[0],
        solver_identity=payload[1],
        proof_status=payload[2],
        root_n=payload[3],
        domain_degree=payload[4],
        block_count=payload[5],
        generator_count=payload[6],
        provenance_digest=payload[7],
        factorization_digest=payload[8],
        proof_identity_sha256=payload[9],
        source_kernel_generators_sha256=payload[10],
        target_kernel_generators_sha256=payload[11],
        work_identity=payload[12],
        order_identity=payload[13],
        dag_status=payload[14],
        dag_unique_nodes=payload[15],
        dag_execution_occurrences=payload[16],
        dag_reused_occurrences=payload[17],
        dag_max_depth=payload[18],
        dag_log2_work_bound_hex=payload[19],
        dag_allowed_log2_work_hex=payload[20],
        external_log2_cost_bound_hex=payload[21],
        seal_sha256=seal_digest,
    )


def _validate_named_integer_identity(
    values: object,
    expected_names: tuple[str, ...],
    *,
    positive_names: frozenset[str],
) -> str | None:
    if type(values) is not tuple or len(values) != len(expected_names):
        return "public replay seal integer identity has the wrong tuple shape"
    names = []
    for item in values:
        if type(item) is not tuple or len(item) != 2 or type(item[0]) is not str or type(item[1]) is not int:
            return "public replay seal integer identity contains a malformed pair"
        name, value = item
        names.append(name)
        if name in positive_names:
            if value < 1:
                return f"public replay seal {name} must be positive"
        elif value < 0:
            return f"public replay seal {name} must be nonnegative"
    if tuple(names) != expected_names:
        return "public replay seal integer identity field order or names drifted"
    return None


def _validate_seal_shape(seal: BlockActionKernelPublicReplaySeal) -> str | None:
    if not isinstance(seal, BlockActionKernelPublicReplaySeal):
        return "seal is not a BlockActionKernelPublicReplaySeal"
    if seal.schema != "block-action-kernel-public-replay-seal-v1":
        return "public replay seal schema is unsupported"
    if seal.solver_identity != (
        "block_action_kernel_proof_dag_consumer_v1",
        "block_action_kernel_public_replay_seal_v1",
        3300,
    ):
        return "public replay seal solver identity drifted"
    if seal.proof_status != _PROOF_STATUS:
        return "public replay seal proof status is not the rev950 exact terminal"
    for name in ("root_n", "domain_degree", "block_count", "dag_unique_nodes", "dag_execution_occurrences"):
        if not _strict_positive_int(getattr(seal, name)):
            return f"public replay seal {name} must be a positive integer"
    for name in ("generator_count", "dag_reused_occurrences", "dag_max_depth"):
        if not _strict_nonnegative_int(getattr(seal, name)):
            return f"public replay seal {name} must be a nonnegative integer"
    if seal.root_n < seal.domain_degree:
        return "public replay seal root does not dominate the original domain"
    if seal.block_count > seal.domain_degree:
        return "public replay seal block count exceeds the original domain"
    if type(seal.dag_status) is not str or not seal.dag_status:
        return "public replay seal proof-DAG status is malformed"
    for name in ("provenance_digest", "factorization_digest"):
        if not _valid_prefixed_digest(getattr(seal, name)):
            return f"public replay seal {name} is malformed"
    for name in (
        "proof_identity_sha256",
        "source_kernel_generators_sha256",
        "target_kernel_generators_sha256",
        "seal_sha256",
    ):
        if not _valid_hex_digest(getattr(seal, name)):
            return f"public replay seal {name} is malformed"

    work_error = _validate_named_integer_identity(
        seal.work_identity,
        _WORK_KEYS,
        positive_names=frozenset({"work_cap"}),
    )
    if work_error is not None:
        return work_error
    order_error = _validate_named_integer_identity(
        seal.order_identity,
        _ORDER_KEYS,
        positive_names=frozenset(_ORDER_KEYS),
    )
    if order_error is not None:
        return order_error
    work = dict(seal.work_identity)
    orders = dict(seal.order_identity)
    if work["estimated_schreier_work_units"] > work["work_cap"]:
        return "public replay seal recorded Schreier work exceeds its cap"
    if orders["source_kernel_order"] * orders["quotient_image_order"] != orders["source_group_order"]:
        return "public replay seal source order factorization drifted"
    if orders["target_kernel_order"] * orders["quotient_image_order"] != orders["target_group_order"]:
        return "public replay seal target order factorization drifted"

    try:
        decoded_bounds = [
            float.fromhex(seal.dag_log2_work_bound_hex),
            float.fromhex(seal.dag_allowed_log2_work_hex),
            float.fromhex(seal.external_log2_cost_bound_hex),
        ]
    except (TypeError, ValueError):
        return "public replay seal accounting hex is malformed"
    if any(not isfinite(value) or value < 0.0 for value in decoded_bounds):
        return "public replay seal accounting bound is not finite and nonnegative"

    payload = (
        seal.schema,
        seal.solver_identity,
        seal.proof_status,
        seal.root_n,
        seal.domain_degree,
        seal.block_count,
        seal.generator_count,
        seal.provenance_digest,
        seal.factorization_digest,
        seal.proof_identity_sha256,
        seal.source_kernel_generators_sha256,
        seal.target_kernel_generators_sha256,
        seal.work_identity,
        seal.order_identity,
        seal.dag_status,
        seal.dag_unique_nodes,
        seal.dag_execution_occurrences,
        seal.dag_reused_occurrences,
        seal.dag_max_depth,
        seal.dag_log2_work_bound_hex,
        seal.dag_allowed_log2_work_hex,
        seal.external_log2_cost_bound_hex,
    )
    if _digest("rev3300-block-action-kernel-public-replay-seal", payload) != seal.seal_sha256:
        return "public replay seal digest does not match its payload"
    return None


def build_block_action_kernel_public_replay_seal(
    provenance,
    certificate,
    *,
    root_n: int | None = None,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> BlockActionKernelPublicReplaySealResult:
    execution = block_action_kernel_proof_dag_consumer(
        provenance,
        certificate,
        root_n=root_n,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not execution.certified:
        return BlockActionKernelPublicReplaySealResult(
            "rev950_execution_not_certified",
            False,
            None,
            execution,
            execution.reason,
        )
    try:
        seal = _build_seal_from_execution(execution)
    except (TypeError, ValueError) as exc:
        return BlockActionKernelPublicReplaySealResult(
            "rev950_execution_not_sealable",
            False,
            None,
            execution,
            str(exc),
        )
    shape_error = _validate_seal_shape(seal)
    if shape_error is not None:
        return BlockActionKernelPublicReplaySealResult(
            "invalid_block_action_kernel_public_replay_seal",
            False,
            seal,
            execution,
            shape_error,
        )
    return BlockActionKernelPublicReplaySealResult(
        "certified_block_action_kernel_public_replay_seal",
        True,
        seal,
        execution,
        "the main-integrated rev950 kernel-factorization proof-DAG is named by one deterministic replay seal",
    )


def verify_block_action_kernel_public_replay_seal(
    provenance,
    certificate,
    seal: BlockActionKernelPublicReplaySeal,
    *,
    root_n: int | None = None,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> BlockActionKernelPublicReplaySealResult:
    shape_error = _validate_seal_shape(seal)
    if shape_error is not None:
        return BlockActionKernelPublicReplaySealResult(
            "invalid_block_action_kernel_public_replay_seal",
            False,
            seal if isinstance(seal, BlockActionKernelPublicReplaySeal) else None,
            None,
            shape_error,
        )
    replayed = build_block_action_kernel_public_replay_seal(
        provenance,
        certificate,
        root_n=root_n,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not replayed.certified or replayed.seal is None:
        return BlockActionKernelPublicReplaySealResult(
            "block_action_kernel_public_replay_execution_failed",
            False,
            seal,
            replayed.execution,
            replayed.reason,
        )
    if replayed.seal != seal:
        return BlockActionKernelPublicReplaySealResult(
            "block_action_kernel_public_replay_seal_mismatch",
            False,
            seal,
            replayed.execution,
            "independent rev950 re-execution produced a different public replay seal",
        )
    return BlockActionKernelPublicReplaySealResult(
        "verified_block_action_kernel_public_replay_seal",
        True,
        seal,
        replayed.execution,
        "independent rev950 re-execution reproduced the exact public replay seal",
    )


__all__ = [
    "BlockActionKernelPublicReplaySeal",
    "BlockActionKernelPublicReplaySealResult",
    "build_block_action_kernel_public_replay_seal",
    "verify_block_action_kernel_public_replay_seal",
]
