from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from math import isfinite, log2
from numbers import Real

from implicit_relation_parent_outcome_v1 import (
    EXACT_EMPTY_STATUSES,
    ParentExactOutcomeContract,
)
from proof_carrying_si_v1 import ProofCarryingCoset
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


_SCHEMA = "implicit-relation-parent-outcome-proof-identity-v1"
_OPERATION = "implicit_relation_parent_outcome_contract_terminal"
_NONEMPTY_STATUS = "exact_implicit_relation_parent_coset"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ParentOutcomeProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    outcome_kind: str
    outcome_status: str
    source_evidence_revision: int
    source_evidence_status: str
    domain_degree: int
    auxiliary_degree: int
    source_relation_digest: str
    target_relation_digest: str
    upstream_artifact_digest: str
    transcript_digest: str
    original_root_n: int
    replay_stable: bool


@dataclass(frozen=True)
class ParentOutcomeProofIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class ParentOutcomeProofDAGConsumerResult:
    status: str
    outcome: ParentExactOutcomeContract | None
    proof: ProofCarryingCoset | None
    identity_validation: ParentOutcomeProofIdentityValidation | None
    dag_validation: ProofDAGValidation | None
    semantic_exactness_certified: bool
    reason: str


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _canonical_transcript_digest(outcome: ParentExactOutcomeContract) -> str:
    payload = {
        "schema_version": 1,
        "source_evidence_revision": outcome.source_evidence_revision,
        "source_evidence_status": outcome.source_evidence_status,
        "outcome_kind": outcome.outcome_kind,
        "exact": outcome.exact,
        "complete": outcome.complete,
        "domain_degree": outcome.domain_degree,
        "auxiliary_degree": outcome.auxiliary_degree,
        "source_relation_digest": outcome.source_relation_digest,
        "target_relation_digest": outcome.target_relation_digest,
        "upstream_artifact_digest": outcome.upstream_artifact_digest,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _validate_exact_outcome_contract(
    outcome: object,
    *,
    original_root_n: int,
) -> tuple[bool, str]:
    if not isinstance(outcome, ParentExactOutcomeContract):
        return False, "outcome must be the main-integrated rev266 ParentExactOutcomeContract"
    if isinstance(original_root_n, bool) or not isinstance(original_root_n, int) or original_root_n < 1:
        return False, "original_root_n must be a positive integer"
    if outcome.exact is not True or outcome.complete is not True:
        return False, "proof-DAG attachment requires an exact complete rev266 outcome"
    if isinstance(outcome.domain_degree, bool) or not isinstance(outcome.domain_degree, int) or outcome.domain_degree < 1:
        return False, "parent outcome domain degree must be positive"
    if outcome.domain_degree > original_root_n:
        return False, "original root must dominate the parent outcome domain"
    if isinstance(outcome.auxiliary_degree, bool) or not isinstance(outcome.auxiliary_degree, int) or outcome.auxiliary_degree < 0:
        return False, "parent outcome auxiliary degree must be nonnegative"
    for field in (
        "source_relation_digest",
        "target_relation_digest",
        "upstream_artifact_digest",
        "transcript_digest",
    ):
        if not _valid_digest(getattr(outcome, field, None)):
            return False, f"{field} is not a canonical lowercase sha256 digest"
    if outcome.transcript_digest != _canonical_transcript_digest(outcome):
        return False, "rev266 transcript digest does not match the canonical outcome fields"

    if outcome.outcome_kind == "nonempty":
        if outcome.status != "exact_parent_outcome_nonempty":
            return False, "nonempty outcome kind requires the rev266 nonempty status"
        if outcome.source_evidence_revision != 261 or outcome.source_evidence_status != _NONEMPTY_STATUS:
            return False, "nonempty outcome is not bound to the rev261 exact parent-coset evidence"
        if outcome.auxiliary_degree < 1:
            return False, "nonempty parent outcome must identify a positive auxiliary degree"
    elif outcome.outcome_kind == "exact_empty":
        if outcome.status != "exact_parent_outcome_empty":
            return False, "exact-empty outcome kind requires the rev266 empty status"
        if outcome.source_evidence_revision != 263 or outcome.source_evidence_status not in EXACT_EMPTY_STATUSES:
            return False, "exact-empty outcome is not bound to an accepted rev263 status"
        if (
            outcome.source_evidence_status == "exact_empty_parent_feature_inventory_mismatch"
            and outcome.auxiliary_degree < 1
        ):
            return False, "feature-inventory exact-empty evidence requires a positive auxiliary degree"
    else:
        return False, "rev266 parent outcome kind is not recognized"
    return True, "rev266 outcome contract is internally replay-consistent"


def _finite_real_value(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        normalized = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    if not isfinite(normalized):
        return None
    return normalized


def _normalize_resource_envelope_arguments(
    *,
    external_log2_cost_bound: object,
    quasipoly_power: object,
    quasipoly_constant: object,
) -> tuple[tuple[float, int, float] | None, str]:
    external = _finite_real_value(external_log2_cost_bound)
    if external is None or external < 0.0:
        return None, "external_log2_cost_bound must be a finite nonnegative real"
    if (
        isinstance(quasipoly_power, bool)
        or not isinstance(quasipoly_power, int)
        or quasipoly_power < 0
    ):
        return None, "quasipoly_power must be a nonnegative integer"
    constant = _finite_real_value(quasipoly_constant)
    if constant is None or constant <= 0.0:
        return None, "quasipoly_constant must be a finite positive real"
    return (
        external,
        int(quasipoly_power),
        constant,
    ), "resource envelope arguments are finite and well typed"


def build_parent_outcome_proof_identity(
    outcome: ParentExactOutcomeContract,
    *,
    original_root_n: int,
) -> ParentOutcomeProofIdentity:
    valid, reason = _validate_exact_outcome_contract(
        outcome,
        original_root_n=original_root_n,
    )
    if not valid:
        raise ValueError(reason)
    return ParentOutcomeProofIdentity(
        schema=_SCHEMA,
        solver_identity=(
            "implicit_relation_parent_outcome_v1",
            "proof_dag_accounting_v1",
            279,
        ),
        outcome_kind=outcome.outcome_kind,
        outcome_status=outcome.status,
        source_evidence_revision=int(outcome.source_evidence_revision),
        source_evidence_status=outcome.source_evidence_status,
        domain_degree=int(outcome.domain_degree),
        auxiliary_degree=int(outcome.auxiliary_degree),
        source_relation_digest=outcome.source_relation_digest,
        target_relation_digest=outcome.target_relation_digest,
        upstream_artifact_digest=outcome.upstream_artifact_digest,
        transcript_digest=outcome.transcript_digest,
        original_root_n=int(original_root_n),
        replay_stable=True,
    )


def _local_log2_cost_bound(identity: ParentOutcomeProofIdentity) -> float:
    """Conservatively charge only immutable-contract replay and digest checking.

    No upstream SI, image action, preimage, or coset computation is replayed here.
    The deliberately loose polynomial term dominates fixed-field validation and
    canonical SHA-256 transcript serialization on the already materialized record.
    """
    n = max(2, identity.domain_degree)
    aux = max(2, identity.auxiliary_degree + 1)
    return 128.0 + 20.0 * log2(n) + 2.0 * log2(aux)


def _proof_from_outcome(
    outcome: ParentExactOutcomeContract,
    identity: ParentOutcomeProofIdentity,
) -> ProofCarryingCoset:
    local_bound = _local_log2_cost_bound(identity)
    accounting = RecurrenceAccountingNode(
        n=identity.original_root_n,
        m=identity.domain_degree,
        operation_kind=_OPERATION,
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=True,
        reason=(
            "replay-stable validation of an already exact rev266 parent outcome contract; "
            "this leaf certifies evidence/accounting only and does not reconstruct an SI coset"
        ),
    )
    return ProofCarryingCoset(
        status="certified_parent_outcome_contract_evidence",
        coset=None,
        operation_kind=_OPERATION,
        root_n=identity.original_root_n,
        domain_size=identity.domain_degree,
        canonical=True,
        exact=False,
        local_cost_certified=True,
        local_log2_cost_bound=local_bound,
        terminal_certified=True,
        children=(),
        accounting=accounting,
        permutation_candidates_checked=0,
        reason=(
            f"rev266 {outcome.outcome_kind} exact-outcome transcript is replay-consistent; "
            "semantic SI exactness is intentionally not promoted by this proof-DAG wrapper"
        ),
        proof_identity=identity,
    )


def validate_parent_outcome_proof_identity(
    proof: ProofCarryingCoset,
    expected: ParentOutcomeProofIdentity,
) -> ParentOutcomeProofIdentityValidation:
    actual = getattr(proof, "proof_identity", None)
    if actual is None:
        return ParentOutcomeProofIdentityValidation(
            "missing_parent_outcome_proof_identity",
            False,
            "parent outcome proof has no execution-linked identity",
        )
    if not isinstance(actual, ParentOutcomeProofIdentity):
        return ParentOutcomeProofIdentityValidation(
            "wrong_parent_outcome_proof_identity_type",
            False,
            "attached identity is not ParentOutcomeProofIdentity v1",
        )
    if actual != expected:
        return ParentOutcomeProofIdentityValidation(
            "mismatched_parent_outcome_proof_identity",
            False,
            "rev266 transcript, root, source evidence, or relation identity differs",
        )
    if not actual.replay_stable:
        return ParentOutcomeProofIdentityValidation(
            "unstable_parent_outcome_proof_identity",
            False,
            "parent outcome identity is not replay-stable",
        )
    try:
        hash(actual)
    except TypeError:
        return ParentOutcomeProofIdentityValidation(
            "unhashable_parent_outcome_proof_identity",
            False,
            "proof-DAG identity must be immutable and hashable",
        )
    if not isinstance(proof, ProofCarryingCoset):
        return ParentOutcomeProofIdentityValidation(
            "wrong_parent_outcome_proof_type",
            False,
            "identity replay requires the canonical ProofCarryingCoset runtime type",
        )
    accounting = getattr(proof, "accounting", None)
    if not isinstance(accounting, RecurrenceAccountingNode):
        return ParentOutcomeProofIdentityValidation(
            "malformed_parent_outcome_accounting_payload",
            False,
            "parent outcome proof must carry one canonical recurrence accounting leaf",
        )
    if (
        proof.status != "certified_parent_outcome_contract_evidence"
        or proof.operation_kind != _OPERATION
        or proof.canonical is not True
        or proof.local_cost_certified is not True
        or proof.terminal_certified is not True
    ):
        return ParentOutcomeProofIdentityValidation(
            "uncertified_parent_outcome_contract_execution",
            False,
            "evidence leaf lacks its canonical terminal accounting contract",
        )
    if proof.exact is not False or proof.coset is not None:
        return ParentOutcomeProofIdentityValidation(
            "semantic_promotion_forbidden_for_parent_outcome_contract",
            False,
            "rev279 must not reinterpret a digest-only rev266 contract as an SI coset proof",
        )
    if (
        isinstance(proof.root_n, bool)
        or not isinstance(proof.root_n, int)
        or isinstance(proof.domain_size, bool)
        or not isinstance(proof.domain_size, int)
        or proof.root_n != actual.original_root_n
        or proof.domain_size != actual.domain_degree
    ):
        return ParentOutcomeProofIdentityValidation(
            "inconsistent_parent_outcome_proof_measure",
            False,
            "proof recurrence measure differs from its frozen parent outcome identity",
        )
    if proof.children != () or accounting.children != ():
        return ParentOutcomeProofIdentityValidation(
            "nonterminal_parent_outcome_evidence_leaf",
            False,
            "rev279 evidence is a terminal replay leaf and cannot carry child executions",
        )
    if (
        isinstance(proof.permutation_candidates_checked, bool)
        or not isinstance(proof.permutation_candidates_checked, int)
        or proof.permutation_candidates_checked != 0
    ):
        return ParentOutcomeProofIdentityValidation(
            "mismatched_parent_outcome_execution_counter",
            False,
            "evidence-only replay must not claim permutation-candidate execution",
        )
    if (
        accounting.operation_kind != _OPERATION
        or isinstance(accounting.n, bool)
        or not isinstance(accounting.n, int)
        or isinstance(accounting.m, bool)
        or not isinstance(accounting.m, int)
        or accounting.n != actual.original_root_n
        or accounting.m != actual.domain_degree
        or accounting.canonical is not True
        or accounting.cost_certified is not True
        or accounting.terminal_certified is not True
    ):
        return ParentOutcomeProofIdentityValidation(
            "mismatched_parent_outcome_accounting_payload",
            False,
            "proof and accounting leaf do not describe the same canonical contract-validation execution",
        )
    proof_local = _finite_real_value(proof.local_log2_cost_bound)
    accounting_local = _finite_real_value(accounting.local_log2_cost_bound)
    expected_local = _local_log2_cost_bound(actual)
    if (
        proof_local is None
        or accounting_local is None
        or proof_local < 0.0
        or accounting_local < 0.0
        or abs(accounting_local - proof_local) > 1e-12
        or abs(proof_local - expected_local) > 1e-12
    ):
        return ParentOutcomeProofIdentityValidation(
            "mismatched_parent_outcome_accounting_payload",
            False,
            "proof/accounting local charge must equal the deterministic conservative charge recomputed from the frozen identity",
        )
    return ParentOutcomeProofIdentityValidation(
        "verified_parent_outcome_proof_identity",
        True,
        "the rev266 outcome contract is bound to the expected replay-stable evidence-only proof identity and its deterministic conservative local charge",
    )


def parent_outcome_contract_proof_dag_consumer(
    outcome: object,
    *,
    original_root_n: int,
    external_log2_cost_bound: float = 0.0,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> ParentOutcomeProofDAGConsumerResult:
    """Attach one already exact rev266 outcome contract to the shared proof DAG.

    The wrapper is deliberately evidence-only.  It validates the rev266 canonical
    transcript independently, freezes the identity, and charges only this replay.
    It never reconstructs the upstream right coset and therefore always keeps
    ``semantic_exactness_certified`` false and the proof's ``exact`` bit false.
    """
    normalized_resource, resource_reason = _normalize_resource_envelope_arguments(
        external_log2_cost_bound=external_log2_cost_bound,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if normalized_resource is None:
        return ParentOutcomeProofDAGConsumerResult(
            "invalid_parent_outcome_resource_envelope",
            outcome if isinstance(outcome, ParentExactOutcomeContract) else None,
            None,
            None,
            None,
            False,
            resource_reason,
        )
    (
        normalized_external_log2_cost_bound,
        normalized_quasipoly_power,
        normalized_quasipoly_constant,
    ) = normalized_resource
    try:
        identity = build_parent_outcome_proof_identity(
            outcome,
            original_root_n=original_root_n,
        )
    except (TypeError, ValueError) as exc:
        return ParentOutcomeProofDAGConsumerResult(
            "invalid_parent_outcome_contract",
            outcome if isinstance(outcome, ParentExactOutcomeContract) else None,
            None,
            None,
            None,
            False,
            str(exc),
        )

    proof = _proof_from_outcome(outcome, identity)
    identity_validation = validate_parent_outcome_proof_identity(proof, identity)
    if not identity_validation.certified:
        return ParentOutcomeProofDAGConsumerResult(
            identity_validation.status,
            outcome,
            proof,
            identity_validation,
            None,
            False,
            identity_validation.reason,
        )

    dag_validation = validate_execution_proof_dag(
        proof,
        original_root_n=int(original_root_n),
        external_log2_cost_bound=normalized_external_log2_cost_bound,
        quasipoly_power=normalized_quasipoly_power,
        quasipoly_constant=normalized_quasipoly_constant,
    )
    if not dag_validation.certified:
        return ParentOutcomeProofDAGConsumerResult(
            dag_validation.status,
            outcome,
            proof,
            identity_validation,
            dag_validation,
            False,
            dag_validation.reason,
        )
    return ParentOutcomeProofDAGConsumerResult(
        "certified_parent_outcome_contract_proof_dag",
        outcome,
        proof,
        identity_validation,
        dag_validation,
        False,
        "rev266 exact-outcome evidence is replay-stably identified and conservatively charged without promoting digest-only evidence to SI semantic exactness",
    )


__all__ = [
    "ParentOutcomeProofIdentity",
    "ParentOutcomeProofIdentityValidation",
    "ParentOutcomeProofDAGConsumerResult",
    "build_parent_outcome_proof_identity",
    "validate_parent_outcome_proof_identity",
    "parent_outcome_contract_proof_dag_consumer",
]
