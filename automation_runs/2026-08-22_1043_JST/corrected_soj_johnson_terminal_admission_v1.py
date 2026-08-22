from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import isfinite, log2
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

_MAIN_RUN = Path(__file__).resolve().parents[1] / "2026-08-19_0851_JST"
if str(_MAIN_RUN) not in sys.path:
    sys.path.insert(0, str(_MAIN_RUN))

from primitive_johnson_ground_terminal_v1 import (  # noqa: E402
    PrimitiveJohnsonGroundProof,
    primitive_johnson_ground_string_isomorphism_terminal,
)
from s1_proof_identity_v1 import (  # noqa: E402
    _contains_opaque,
    _freeze_group,
    _freeze_identity_value,
)


SCHEMA_VERSION = 1
EXPECTED_STATUS = "certified_corrected_soj_explicit_johnson_embedding"
EXPECTED_KIND = "johnson_embedding"


@dataclass(frozen=True)
class CorrectedSOJJohnsonTransitionSnapshot:
    status: str
    transition_kind: str
    theorem_input_gate: bool
    canonical: bool
    exact: bool
    progress_certified: bool
    multiplicative_cost: float
    max_multiplicative_cost: float
    johnson_ground_size: int
    johnson_subset_size: int
    johnson_vertex_count: int


@dataclass(frozen=True)
class CorrectedSOJJohnsonTerminalIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    transition_identity: tuple[object, ...]
    embedding_identity: tuple[tuple[int, ...], ...]
    pair_relation_identity: tuple[tuple[int, int, int], ...]
    group_identity: tuple
    source_identity: tuple[object, ...]
    target_identity: tuple[object, ...]
    root_n: int
    resource_identity: tuple[tuple[str, object], ...]
    replay_stable: bool


@dataclass(frozen=True)
class CorrectedSOJJohnsonTerminalAdmission:
    schema_version: int
    status: str
    certified: bool
    transition: CorrectedSOJJohnsonTransitionSnapshot | None
    terminal_proof: PrimitiveJohnsonGroundProof | None
    identity: CorrectedSOJJohnsonTerminalIdentity | None
    transition_log2_cost_bound: float
    combined_log2_work_bound: float
    allowed_log2_work: float
    admission_digest: str
    reason: str


def _fail(
    reason: str,
    *,
    transition: CorrectedSOJJohnsonTransitionSnapshot | None = None,
    proof: PrimitiveJohnsonGroundProof | None = None,
    identity: CorrectedSOJJohnsonTerminalIdentity | None = None,
    transition_charge: float = 0.0,
    combined: float = 0.0,
    allowed: float = 0.0,
    status: str = "corrected_soj_johnson_terminal_not_certified",
) -> CorrectedSOJJohnsonTerminalAdmission:
    return CorrectedSOJJohnsonTerminalAdmission(
        SCHEMA_VERSION,
        status,
        False,
        transition,
        proof,
        identity,
        transition_charge,
        combined,
        allowed,
        "",
        reason,
    )


def _field(obj: Any, name: str):
    if not hasattr(obj, name):
        raise ValueError(f"transition is missing required field {name!r}")
    return getattr(obj, name)


def _snapshot(transition: Any) -> CorrectedSOJJohnsonTransitionSnapshot:
    ground = _field(transition, "johnson_ground_size")
    subset = _field(transition, "johnson_subset_size")
    vertices = _field(transition, "johnson_vertex_count")
    if ground is None or subset is None or vertices is None:
        raise ValueError("explicit Johnson transition is missing its structural dimensions")
    return CorrectedSOJJohnsonTransitionSnapshot(
        status=str(_field(transition, "status")),
        transition_kind=str(_field(transition, "transition_kind")),
        theorem_input_gate=bool(_field(transition, "theorem_input_gate")),
        canonical=bool(_field(transition, "canonical")),
        exact=bool(_field(transition, "exact")),
        progress_certified=bool(_field(transition, "progress_certified")),
        multiplicative_cost=float(_field(transition, "multiplicative_cost")),
        max_multiplicative_cost=float(_field(transition, "max_multiplicative_cost")),
        johnson_ground_size=int(ground),
        johnson_subset_size=int(subset),
        johnson_vertex_count=int(vertices),
    )


def _validate_transition_shape(snap: CorrectedSOJJohnsonTransitionSnapshot) -> str | None:
    if snap.status != EXPECTED_STATUS or snap.transition_kind != EXPECTED_KIND:
        return "only a certified explicit Johnson-embedding transition is admitted here"
    if not snap.theorem_input_gate:
        return "the corrected bipartite Split-or-Johnson theorem-input gate is not certified"
    if not snap.canonical or not snap.exact or not snap.progress_certified:
        return "transition must be canonical, exact, and progress-certified"
    if not isfinite(snap.multiplicative_cost) or snap.multiplicative_cost <= 0.0:
        return "transition multiplicative cost must be finite and positive"
    if not isfinite(snap.max_multiplicative_cost) or snap.max_multiplicative_cost <= 0.0:
        return "transition multiplicative-cost bound must be finite and positive"
    if snap.multiplicative_cost > snap.max_multiplicative_cost:
        return "transition multiplicative cost exceeds its certified upper bound"
    m = snap.johnson_ground_size
    k = snap.johnson_subset_size
    if m < 4 or not 2 <= k <= m - 2 or snap.johnson_vertex_count <= 0:
        return "transition carries malformed Johnson structural dimensions"
    return None


def _normalize_embedding(
    embedding: Iterable[Iterable[int]],
    *,
    ground_size: int,
    subset_size: int,
    vertex_count: int,
) -> tuple[tuple[int, ...], ...]:
    coords = tuple(tuple(sorted({int(x) for x in xs})) for xs in embedding)
    if len(coords) != vertex_count:
        raise ValueError("explicit Johnson embedding length differs from the certified vertex count")
    if not coords:
        raise ValueError("explicit Johnson embedding is empty")
    for xs in coords:
        if len(xs) != subset_size or any(x < 0 or x >= ground_size for x in xs):
            raise ValueError("explicit Johnson embedding contains a malformed coordinate")
    if len(set(coords)) != len(coords):
        raise ValueError("explicit Johnson embedding is not injective")
    return coords


def _normalize_pair_relation(
    pair_relation_distance: Mapping[tuple[int, int], int],
    coords: tuple[tuple[int, ...], ...],
    *,
    subset_size: int,
) -> tuple[tuple[int, int, int], ...]:
    n = len(coords)
    expected_keys = {(i, j) for i in range(n) for j in range(i + 1, n)}
    supplied_keys = {(int(i), int(j)) for i, j in pair_relation_distance}
    if supplied_keys != expected_keys or len(pair_relation_distance) != len(expected_keys):
        raise ValueError("pair relation certificate must cover every unordered embedded pair exactly once")
    coord_sets = tuple(frozenset(xs) for xs in coords)
    rows = []
    for i, j in sorted(expected_keys):
        value = int(pair_relation_distance[(i, j)])
        expected = subset_size - len(coord_sets[i] & coord_sets[j])
        if value != expected:
            raise ValueError("pair relation does not equal the explicit Johnson intersection relation")
        rows.append((i, j, value))
    return tuple(rows)


def _relation_lookup(rows: tuple[tuple[int, int, int], ...]) -> dict[tuple[int, int], int]:
    return {(i, j): value for i, j, value in rows}


def _pair_value(relation: Mapping[tuple[int, int], int], i: int, j: int) -> int:
    if i == j:
        return 0
    return relation[(i, j) if i < j else (j, i)]


def _validate_ambient_invariance(group, rows: tuple[tuple[int, int, int], ...]) -> str | None:
    relation = _relation_lookup(rows)
    n = int(group.degree)
    for generator in group.original_generators:
        if len(generator) != n or sorted(generator) != list(range(n)):
            return "ambient group contains a malformed original generator"
        for i in range(n):
            for j in range(i + 1, n):
                if _pair_value(relation, i, j) != _pair_value(
                    relation, int(generator[i]), int(generator[j])
                ):
                    return "ambient group generator does not preserve the supplied explicit Johnson relation"
    return None


def _build_identity(
    snap: CorrectedSOJJohnsonTransitionSnapshot,
    coords: tuple[tuple[int, ...], ...],
    rows: tuple[tuple[int, int, int], ...],
    group,
    source: tuple[object, ...],
    target: tuple[object, ...],
    *,
    root_n: int,
    polylog_power: int,
    max_ground_degree: int,
    max_recognition_nodes: int,
    transition_cost_bound_certified: bool,
) -> CorrectedSOJJohnsonTerminalIdentity:
    source_identity = tuple(_freeze_identity_value(x) for x in source)
    target_identity = tuple(_freeze_identity_value(x) for x in target)
    transition_identity = (
        snap.status,
        snap.transition_kind,
        snap.theorem_input_gate,
        snap.canonical,
        snap.exact,
        snap.progress_certified,
        snap.multiplicative_cost,
        snap.max_multiplicative_cost,
        snap.johnson_ground_size,
        snap.johnson_subset_size,
        snap.johnson_vertex_count,
    )
    resources: tuple[tuple[str, object], ...] = (
        ("polylog_power", int(polylog_power)),
        ("max_ground_degree", int(max_ground_degree)),
        ("max_recognition_nodes", int(max_recognition_nodes)),
        ("transition_cost_bound_certified", bool(transition_cost_bound_certified)),
    )
    return CorrectedSOJJohnsonTerminalIdentity(
        "corrected-soj-johnson-terminal-admission-identity-v1",
        ("corrected_soj_johnson_terminal_admission_v1", "primitive_johnson_ground_terminal_v1", 284),
        transition_identity,
        coords,
        rows,
        _freeze_group(group),
        source_identity,
        target_identity,
        int(root_n),
        resources,
        not any(_contains_opaque(x) for x in source_identity + target_identity),
    )


def _proof_summary(proof: PrimitiveJohnsonGroundProof) -> dict[str, object]:
    coset = proof.coset
    if coset is None:
        coset_summary: object = None
    else:
        coset_summary = {
            "representative": tuple(int(x) for x in coset.representative),
            "subgroup_order": int(coset.subgroup.order),
            "subgroup_generators": tuple(
                tuple(int(x) for x in g) for g in coset.subgroup.original_generators
            ),
        }
    return {
        "status": proof.status,
        "exact": bool(proof.exact),
        "operation_kind": proof.operation_kind,
        "root_n": int(proof.root_n),
        "domain_size": int(proof.domain_size),
        "canonical": bool(proof.canonical),
        "local_cost_certified": bool(proof.local_cost_certified),
        "terminal_certified": bool(proof.terminal_certified),
        "local_log2_cost_bound": float(proof.local_log2_cost_bound),
        "johnson_ground_size": int(proof.johnson_ground_size),
        "johnson_subset_size": int(proof.johnson_subset_size),
        "ground_permutations_checked": int(proof.ground_permutations_checked),
        "recognition_search_nodes": int(proof.recognition_search_nodes),
        "coset": coset_summary,
    }


def _digest(
    identity: CorrectedSOJJohnsonTerminalIdentity,
    proof: PrimitiveJohnsonGroundProof,
    transition_charge: float,
    combined: float,
    allowed: float,
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "identity": identity.__dict__,
        "proof": _proof_summary(proof),
        "transition_log2_cost_bound": float(transition_charge),
        "combined_log2_work_bound": float(combined),
        "allowed_log2_work": float(allowed),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=list).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def admit_corrected_soj_johnson_small_ground_terminal(
    transition: Any,
    *,
    embedding: Iterable[Iterable[int]],
    pair_relation_distance: Mapping[tuple[int, int], int],
    group,
    source_values: Iterable[object],
    target_values: Iterable[object],
    root_n: int,
    transition_cost_bound_certified: bool,
    polylog_power: int = 2,
    max_ground_degree: int = 8,
    max_recognition_nodes: int = 500000,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> CorrectedSOJJohnsonTerminalAdmission:
    """Admit an explicit corrected-SOJ Johnson transition to the exact small-ground terminal.

    The active transition branch is not imported.  Its public structural shape is
    independently revalidated, including the full caller-supplied embedding and
    pair relation.  Every ambient generator must preserve that relation, and the
    main-integrated primitive-Johnson terminal must independently recognize the
    same ``J(v,k)`` parameters and return an exact terminal result.

    Larger Johnson grounds remain a recursive structural case.  This adapter does
    not turn a Johnson label into an ``aux_shrink`` recurrence edge and does not
    claim corrected Split-or-Johnson closure.
    """
    try:
        snap = _snapshot(transition)
    except (TypeError, ValueError) as exc:
        return _fail(str(exc))
    reason = _validate_transition_shape(snap)
    if reason is not None:
        return _fail(reason, transition=snap)
    if not transition_cost_bound_certified:
        return _fail(
            "terminal admission does not manufacture a transition cost certificate",
            transition=snap,
        )
    if not hasattr(group, "degree") or not hasattr(group, "original_generators"):
        return _fail("ambient group is not a deterministic Schreier-chain group", transition=snap)
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    root = int(root_n)
    if n != snap.johnson_vertex_count:
        return _fail("ambient group degree differs from the certified Johnson vertex count", transition=snap)
    if len(source) != n or len(target) != n:
        return _fail("source/target strings must cover the complete ambient domain", transition=snap)
    if root <= 0 or root < n:
        return _fail("root_n must dominate the Johnson action domain", transition=snap)
    if polylog_power < 1 or max_ground_degree < 1 or max_recognition_nodes < 1:
        return _fail("invalid primitive-Johnson terminal resource parameter", transition=snap)
    if quasipoly_power < 1 or quasipoly_constant <= 0.0:
        return _fail("invalid local quasipolynomial envelope parameter", transition=snap)

    try:
        coords = _normalize_embedding(
            embedding,
            ground_size=snap.johnson_ground_size,
            subset_size=snap.johnson_subset_size,
            vertex_count=snap.johnson_vertex_count,
        )
        rows = _normalize_pair_relation(
            pair_relation_distance,
            coords,
            subset_size=snap.johnson_subset_size,
        )
    except (TypeError, ValueError, KeyError) as exc:
        return _fail(str(exc), transition=snap)

    reason = _validate_ambient_invariance(group, rows)
    if reason is not None:
        return _fail(reason, transition=snap)

    identity = _build_identity(
        snap,
        coords,
        rows,
        group,
        source,
        target,
        root_n=root,
        polylog_power=polylog_power,
        max_ground_degree=max_ground_degree,
        max_recognition_nodes=max_recognition_nodes,
        transition_cost_bound_certified=transition_cost_bound_certified,
    )
    if not identity.replay_stable:
        return _fail(
            "opaque source/target values do not provide a replay-stable mathematical identity",
            transition=snap,
            identity=identity,
            status="unstable_corrected_soj_johnson_terminal_identity",
        )

    proof = primitive_johnson_ground_string_isomorphism_terminal(
        group,
        source,
        target,
        root_n=root,
        polylog_power=polylog_power,
        max_ground_degree=max_ground_degree,
        max_recognition_nodes=max_recognition_nodes,
    )
    if not proof.exact:
        return _fail(
            "the explicit Johnson transition is structurally certified, but the main small-ground terminal did not close exactly: "
            + proof.reason,
            transition=snap,
            proof=proof,
            identity=identity,
            status="corrected_soj_johnson_requires_recursive_ground_handling",
        )
    if proof.status not in {"exact_primitive_johnson_ground_coset", "exact_empty_primitive_johnson_ground"}:
        return _fail("unexpected exact primitive-Johnson terminal status", transition=snap, proof=proof, identity=identity)
    if not (
        proof.canonical
        and proof.local_cost_certified
        and proof.terminal_certified
        and proof.operation_kind == "primitive_johnson_ground_terminal"
    ):
        return _fail("primitive-Johnson result lacks exact terminal accounting certification", transition=snap, proof=proof, identity=identity)
    if proof.johnson_ground_size != snap.johnson_ground_size or proof.johnson_subset_size != snap.johnson_subset_size:
        return _fail(
            "main ambient-action recognition disagrees with the explicit transition Johnson parameters",
            transition=snap,
            proof=proof,
            identity=identity,
            status="corrected_soj_johnson_ambient_recognition_mismatch",
        )

    transition_charge = max(0.0, log2(snap.max_multiplicative_cost))
    combined = transition_charge + float(proof.local_log2_cost_bound)
    allowed = float(quasipoly_constant) * (log2(max(2, root)) ** int(quasipoly_power))
    if combined > allowed + 1e-9:
        return _fail(
            "transition plus exact small-ground terminal exceeds the configured local root envelope",
            transition=snap,
            proof=proof,
            identity=identity,
            transition_charge=transition_charge,
            combined=combined,
            allowed=allowed,
            status="corrected_soj_johnson_terminal_envelope_exceeded",
        )

    digest = _digest(identity, proof, transition_charge, combined, allowed)
    return CorrectedSOJJohnsonTerminalAdmission(
        SCHEMA_VERSION,
        "certified_corrected_soj_johnson_small_ground_terminal",
        True,
        snap,
        proof,
        identity,
        transition_charge,
        combined,
        allowed,
        digest,
        "the explicit Johnson transition is replay-stably bound to an invariant-compatible ambient action and the main-integrated exact small-ground Johnson terminal",
    )


def replay_corrected_soj_johnson_small_ground_terminal(
    admission: CorrectedSOJJohnsonTerminalAdmission,
    transition: Any,
    **kwargs,
) -> bool:
    if not isinstance(admission, CorrectedSOJJohnsonTerminalAdmission) or not admission.certified:
        return False
    replay = admit_corrected_soj_johnson_small_ground_terminal(transition, **kwargs)
    return bool(
        replay.certified
        and replay.status == admission.status
        and replay.identity == admission.identity
        and replay.admission_digest == admission.admission_digest
    )


__all__ = [
    "CorrectedSOJJohnsonTransitionSnapshot",
    "CorrectedSOJJohnsonTerminalIdentity",
    "CorrectedSOJJohnsonTerminalAdmission",
    "admit_corrected_soj_johnson_small_ground_terminal",
    "replay_corrected_soj_johnson_small_ground_terminal",
]
