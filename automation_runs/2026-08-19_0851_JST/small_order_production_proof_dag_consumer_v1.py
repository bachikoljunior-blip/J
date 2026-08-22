from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from math import isclose, isfinite, log2

from exact_result_replay_verifier_v1 import CertificateBuildError, ReplayStatus, build_certificate
from permutation_group_schreier import identity
from proof_carrying_small_order_production_admission_v1 import (
    ProductionAdmissionCaps,
    ProductionAdmissionStatus,
    SmallOrderProductionAdmission,
    preflight_small_order_production_admission,
    verify_small_order_production_result,
)
from proof_carrying_small_order_si_v1 import (
    SmallOrderProofCarryingCoset,
    exact_small_order_group_string_isomorphism,
)
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from s1_proof_identity_v1 import _contains_opaque, _freeze_group, _freeze_identity_value


_EXACT_STATUSES = frozenset({"exact_small_order_group_coset", "exact_empty_small_order_group"})


@dataclass(frozen=True)
class SmallOrderProductionProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    group_identity: tuple
    source_identity: tuple[object, ...]
    target_identity: tuple[object, ...]
    root_n: int
    domain_size: int
    certified_group_order: int
    producer_status: str
    producer_group_elements_checked: int
    claimed_match_count: int
    certificate_sha256: str
    replay_identity: tuple
    recurrence_status: str
    resource_identity: tuple[tuple[str, int], ...]
    external_log2_cost_bound: float
    replay_stable: bool


@dataclass(frozen=True)
class SmallOrderProductionIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class SmallOrderProductionProofDAGConsumerResult:
    status: str
    proof: SmallOrderProofCarryingCoset | None
    admission: SmallOrderProductionAdmission | None
    identity_validation: SmallOrderProductionIdentityValidation | None
    dag_validation: ProofDAGValidation | None
    reason: str

    @property
    def certified(self) -> bool:
        return bool(self.dag_validation is not None and self.dag_validation.certified)


def _resource_identity(caps: ProductionAdmissionCaps, group_order_poly_power: int):
    return (
        ("group_order_poly_power", int(group_order_poly_power)),
        ("max_action_point_checks", int(caps.max_action_point_checks)),
        ("max_certificate_bytes", int(caps.max_certificate_bytes)),
        ("max_degree", int(caps.max_degree)),
        ("max_group_compositions", int(caps.max_group_compositions)),
        ("max_group_order", int(caps.max_group_order)),
    )


def _verification_external_log2_cost(admission: SmallOrderProductionAdmission, caps: ProductionAdmissionCaps) -> float:
    """Conservatively charge rev252 independent enumeration/replay outside the producer leaf."""
    replay = admission.replay
    if replay is None:
        raise ValueError("an admitted rev252 result must carry replay evidence")
    preflight = admission.preflight
    units = (
        1
        + int(preflight.required_group_compositions)
        + int(preflight.required_action_point_checks)
        + int(replay.group_compositions)
        + int(replay.action_point_checks)
        + int(caps.max_certificate_bytes)
        + int(preflight.group_order) * max(1, int(preflight.degree))
    )
    return log2(max(1, units)) + 16.0 * log2(max(2, int(preflight.degree))) + 32.0


def _snapshot_inputs(group, source_values, target_values):
    try:
        source = tuple(deepcopy(tuple(source_values)))
        target = tuple(deepcopy(tuple(target_values)))
        n = int(group.degree)
        build_certificate(
            source=source,
            target=target,
            candidate_group=(identity(n),),
            claimed_matches=(),
            universe_label="rev620-input-snapshot-probe",
            solver_status="exact",
        )
    except (CertificateBuildError, TypeError, ValueError, RecursionError) as exc:
        return None, None, str(exc)
    return source, target, None


def build_small_order_production_identity(
    group,
    source_values,
    target_values,
    proof: SmallOrderProofCarryingCoset,
    admission: SmallOrderProductionAdmission,
    *,
    group_order_poly_power: int,
    caps: ProductionAdmissionCaps,
) -> SmallOrderProductionProofIdentity:
    if not admission.admitted or admission.status is not ProductionAdmissionStatus.ADMITTED_EXACT:
        raise ValueError("only rev252-admitted exact executions may receive a proof-DAG identity")
    if admission.replay is None or admission.replay.status is not ReplayStatus.VERIFIED_EXACT:
        raise ValueError("rev252 admission lacks verified exact replay evidence")
    if not admission.certificate_sha256 or len(admission.certificate_sha256) != 64:
        raise ValueError("rev252 admission lacks a stable replay certificate digest")
    if proof.status not in _EXACT_STATUSES or not proof.exact:
        raise ValueError("only an exact small-order producer may receive a proof-DAG identity")

    source_identity = tuple(_freeze_identity_value(value) for value in tuple(source_values))
    target_identity = tuple(_freeze_identity_value(value) for value in tuple(target_values))
    replay = admission.replay
    external = _verification_external_log2_cost(admission, caps)
    replay_identity = (
        str(replay.status.value),
        str(replay.certificate_sha256),
        int(replay.degree),
        int(replay.group_size),
        int(replay.claimed_match_count),
        int(replay.replayed_match_count),
        None if replay.target_stabilizer_size is None else int(replay.target_stabilizer_size),
        int(replay.group_compositions),
        int(replay.action_point_checks),
    )
    replay_stable = (
        not any(_contains_opaque(value) for value in source_identity + target_identity)
        and isfinite(float(proof.local_log2_cost_bound))
        and isfinite(external)
    )
    return SmallOrderProductionProofIdentity(
        "small-order-production-proof-identity-v1",
        ("proof_carrying_small_order_production_admission_v1", "proof_dag_accounting_v1", 620),
        _freeze_group(group),
        source_identity,
        target_identity,
        int(admission.preflight.root_n),
        int(admission.preflight.degree),
        int(admission.preflight.group_order),
        str(proof.status),
        int(proof.group_elements_checked),
        int(admission.claimed_match_count),
        str(admission.certificate_sha256),
        replay_identity,
        str(admission.recurrence_status),
        _resource_identity(caps, group_order_poly_power),
        external,
        replay_stable,
    )


def validate_small_order_production_identity(
    proof: SmallOrderProofCarryingCoset,
    admission: SmallOrderProductionAdmission,
    expected: SmallOrderProductionProofIdentity,
) -> SmallOrderProductionIdentityValidation:
    actual = getattr(proof, "proof_identity", None)
    if actual is None:
        return SmallOrderProductionIdentityValidation(
            "missing_small_order_production_proof_identity", False,
            "the rev252-admitted producer has no execution-linked proof identity",
        )
    if not isinstance(actual, SmallOrderProductionProofIdentity):
        return SmallOrderProductionIdentityValidation(
            "wrong_small_order_production_proof_identity_type", False,
            "the attached identity is not SmallOrderProductionProofIdentity v1",
        )
    if actual != expected:
        return SmallOrderProductionIdentityValidation(
            "mismatched_small_order_production_proof_identity", False,
            "group, strings, root, resource gates, replay certificate, or exact producer payload differs",
        )
    if not actual.replay_stable:
        return SmallOrderProductionIdentityValidation(
            "unstable_small_order_production_proof_identity", False,
            "opaque values or non-finite charges cannot name a reusable proof-DAG node",
        )
    if not admission.admitted or admission.status is not ProductionAdmissionStatus.ADMITTED_EXACT:
        return SmallOrderProductionIdentityValidation(
            "small_order_production_not_admitted", False,
            "rev252 did not independently admit the producer as exact",
        )
    replay = admission.replay
    if replay is None or replay.status is not ReplayStatus.VERIFIED_EXACT:
        return SmallOrderProductionIdentityValidation(
            "small_order_production_replay_not_exact", False,
            "the independent rev252 replay is absent or nonexact",
        )
    if (
        admission.certificate_sha256 != actual.certificate_sha256
        or replay.certificate_sha256 != actual.certificate_sha256
        or admission.recurrence_status != actual.recurrence_status
        or not admission.recurrence_certified
        or admission.preflight.root_n != actual.root_n
        or admission.preflight.degree != actual.domain_size
        or admission.preflight.group_order != actual.certified_group_order
        or admission.producer_status != actual.producer_status
        or admission.producer_group_elements_checked != actual.producer_group_elements_checked
        or admission.claimed_match_count != actual.claimed_match_count
    ):
        return SmallOrderProductionIdentityValidation(
            "inconsistent_small_order_production_admission", False,
            "rev252 replay/recurrence/preflight fields differ from the frozen execution identity",
        )
    if not (
        proof.status == actual.producer_status
        and proof.status in _EXACT_STATUSES
        and proof.exact
        and proof.canonical
        and proof.local_cost_certified
        and proof.terminal_certified
        and proof.operation_kind == "small_order_group_si_terminal"
        and not proof.children
        and proof.root_n == actual.root_n
        and proof.domain_size == actual.domain_size
        and proof.certified_group_order == actual.certified_group_order
        and proof.group_elements_checked == actual.producer_group_elements_checked
        and proof.permutation_candidates_checked == proof.group_elements_checked
    ):
        return SmallOrderProductionIdentityValidation(
            "inconsistent_small_order_producer_payload", False,
            "the exact producer payload differs from the rev252-bound execution identity",
        )
    expected_scans = actual.certified_group_order * (
        2 if actual.producer_status == "exact_small_order_group_coset" else 1
    )
    if actual.producer_group_elements_checked != expected_scans:
        return SmallOrderProductionIdentityValidation(
            "small_order_producer_scan_count_drift", False,
            "the exact producer scan count no longer matches the full-enumeration/audit contract",
        )
    if actual.producer_status == "exact_small_order_group_coset":
        if proof.coset is None or proof.coset.subgroup.degree != actual.domain_size:
            return SmallOrderProductionIdentityValidation(
                "invalid_small_order_nonempty_coset", False,
                "the exact nonempty status must carry an original-domain right coset",
            )
    elif proof.coset is not None:
        return SmallOrderProductionIdentityValidation(
            "invalid_small_order_empty_coset", False,
            "the exact-empty status must not carry a right coset",
        )
    accounting = proof.accounting
    if not (
        accounting.n == actual.root_n
        and accounting.m == max(1, actual.domain_size)
        and accounting.operation_kind == "small_order_group_si_terminal"
        and accounting.canonical
        and accounting.cost_certified
        and accounting.terminal_certified
        and not accounting.children
        and isfinite(float(accounting.local_log2_cost_bound))
        and isclose(
            float(accounting.local_log2_cost_bound),
            float(proof.local_log2_cost_bound),
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ):
        return SmallOrderProductionIdentityValidation(
            "inconsistent_small_order_production_accounting", False,
            "the recurrence leaf differs from the exact producer identity",
        )
    resources = dict(actual.resource_identity)
    if actual.certified_group_order > min(
        resources["max_group_order"], actual.root_n ** resources["group_order_poly_power"]
    ):
        return SmallOrderProductionIdentityValidation(
            "small_order_production_order_gate_drift", False,
            "the exact execution exceeds the frozen polynomial/hard small-order gate",
        )
    if not isfinite(actual.external_log2_cost_bound) or actual.external_log2_cost_bound < 0.0:
        return SmallOrderProductionIdentityValidation(
            "invalid_small_order_replay_charge", False,
            "the independently replayed production admission must carry a finite nonnegative external charge",
        )
    return SmallOrderProductionIdentityValidation(
        "verified_small_order_production_proof_identity", True,
        "the exact producer, rev252 independent replay, recurrence leaf, certificate digest, and resource gates share one replay-stable identity",
    )


def small_order_production_proof_dag_consumer(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    group_order_poly_power: int = 2,
    caps: ProductionAdmissionCaps = ProductionAdmissionCaps(),
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> SmallOrderProductionProofDAGConsumerResult:
    """Execute the rev252 production boundary once and admit only replay-verified exact evidence."""
    source, target, snapshot_error = _snapshot_inputs(group, source_values, target_values)
    if snapshot_error is not None:
        return SmallOrderProductionProofDAGConsumerResult(
            "rejected_small_order_input_snapshot", None, None, None, None,
            f"input cannot be snapshotted deterministically: {snapshot_error}",
        )
    preflight = preflight_small_order_production_admission(
        group,
        source,
        target,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        caps=caps,
    )
    if not preflight.admitted:
        return SmallOrderProductionProofDAGConsumerResult(
            "small_order_production_resource_cap", None, None, None, None,
            preflight.reason,
        )
    producer = exact_small_order_group_string_isomorphism(
        group,
        source,
        target,
        root_n=preflight.root_n,
        group_order_poly_power=group_order_poly_power,
        max_group_order=caps.max_group_order,
    )
    admission = verify_small_order_production_result(
        group,
        source,
        target,
        producer,
        root_n=preflight.root_n,
        group_order_poly_power=group_order_poly_power,
        caps=caps,
        preflight=preflight,
    )
    if not admission.admitted:
        return SmallOrderProductionProofDAGConsumerResult(
            "small_order_production_not_exactly_admitted", producer, admission, None, None,
            admission.reason,
        )
    expected = build_small_order_production_identity(
        group,
        source,
        target,
        producer,
        admission,
        group_order_poly_power=group_order_poly_power,
        caps=caps,
    )
    attached = replace(producer, proof_identity=expected)
    identity_validation = validate_small_order_production_identity(attached, admission, expected)
    if not identity_validation.certified:
        return SmallOrderProductionProofDAGConsumerResult(
            identity_validation.status, attached, admission, identity_validation, None,
            identity_validation.reason,
        )
    dag = validate_execution_proof_dag(
        attached,
        original_root_n=expected.root_n,
        external_log2_cost_bound=expected.external_log2_cost_bound,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not dag.certified:
        return SmallOrderProductionProofDAGConsumerResult(
            dag.status, attached, admission, identity_validation, dag, dag.reason,
        )
    return SmallOrderProductionProofDAGConsumerResult(
        "certified_small_order_production_proof_dag",
        attached,
        admission,
        identity_validation,
        dag,
        "the exact rev252 production admission is replay-stably identified and conservatively occurrence-charged by the shared execution proof DAG, with independent replay charged externally",
    )


__all__ = [
    "SmallOrderProductionProofIdentity",
    "SmallOrderProductionIdentityValidation",
    "SmallOrderProductionProofDAGConsumerResult",
    "build_small_order_production_identity",
    "validate_small_order_production_identity",
    "small_order_production_proof_dag_consumer",
]
