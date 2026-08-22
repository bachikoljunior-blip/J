from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REV287_DIR = _REPO_ROOT / "automation_runs" / "2026-08-22_1155_JST"
if str(_REV287_DIR) not in sys.path:
    sys.path.insert(0, str(_REV287_DIR))

from corrected_soj_johnson_relational_reduction_v1 import (  # noqa: E402
    JohnsonGroundRelationalReductionEvidence,
    replay_johnson_ground_relational_reduction,
)

SCHEMA_VERSION = 1
STATUS = "certified_johnson_child_semantic_projection"
PROFILE_KIND = "incident_parent_color_multiset_v1"
_SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class JohnsonChildSemanticBinding:
    schema_version: int
    status: str
    certified: bool
    canonical: bool
    replay_stable: bool
    parent_to_child_transport_certified: bool
    child_to_parent_transport_certified: bool
    parent_solution_equivalence_certified: bool
    source_action_degree: int
    child_ground_size: int
    johnson_subset_size: int
    profile_kind: str
    reduction_identity: str
    parent_source_digest: str
    parent_target_digest: str
    child_source_digest: str
    child_target_digest: str
    child_source_values: tuple[Any, ...]
    child_target_values: tuple[Any, ...]
    semantic_work_bound: int
    binding_identity: str
    reason: str


def _fail(reason: str, *, n: int = 0, v: int = 0, k: int = 0) -> JohnsonChildSemanticBinding:
    return JohnsonChildSemanticBinding(
        SCHEMA_VERSION,
        "johnson_child_semantic_projection_not_certified",
        False,
        False,
        False,
        False,
        False,
        False,
        n,
        v,
        k,
        PROFILE_KIND,
        "",
        "",
        "",
        "",
        "",
        (),
        (),
        0,
        "",
        reason,
    )


def _strict_sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _strict_int(value: Any, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be a strict integer")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _freeze_value(value: Any, path: str = "value") -> Any:
    if value is None:
        return ("none",)
    if type(value) is bool:
        return ("bool", value)
    if type(value) is int:
        return ("int", str(value))
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} float must be finite")
        return ("float", value.hex())
    if type(value) is str:
        return ("str", value)
    if type(value) is bytes:
        return ("bytes", value.hex())
    if type(value) in (list, tuple):
        return ("sequence", tuple(_freeze_value(item, f"{path}[{index}]") for index, item in enumerate(value)))
    if type(value) is dict:
        items: list[tuple[str, Any]] = []
        for key in sorted(value):
            if type(key) is not str:
                raise ValueError(f"{path} mapping keys must be strings")
            items.append((key, _freeze_value(value[key], f"{path}.{key}")))
        return ("mapping", tuple(items))
    raise ValueError(f"{path} has opaque/non-replay-stable type {type(value).__name__}")


def _normalize_parent_values(values: Any, *, degree: int, name: str) -> tuple[Any, ...]:
    seq = _strict_sequence(values, name)
    if len(seq) != degree:
        raise ValueError(f"{name} length does not equal the certified parent action degree")
    return tuple(_freeze_value(value, f"{name}[{index}]") for index, value in enumerate(seq))


def _normalize_permutation(raw: Any, *, degree: int, name: str) -> tuple[int, ...]:
    seq = _strict_sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong degree")
    out = tuple(_strict_int(value, f"{name}[{index}]") for index, value in enumerate(seq))
    if any(value < 0 or value >= degree for value in out) or len(set(out)) != degree:
        raise ValueError(f"{name} is not a permutation of the certified ground")
    return out


def _transport(values: Sequence[Any], permutation: Sequence[int]) -> tuple[Any, ...]:
    if len(values) != len(permutation):
        raise ValueError("transport dimension mismatch")
    out: list[Any] = [None] * len(values)
    for source, target in enumerate(permutation):
        out[target] = values[source]
    return tuple(out)


def _profile(values: tuple[Any, ...], star: Sequence[int]) -> tuple[Any, ...]:
    counts: dict[bytes, tuple[Any, int]] = {}
    for vertex in star:
        token = values[vertex]
        key = _canonical_bytes(token)
        previous = counts.get(key)
        counts[key] = (token, 1 if previous is None else previous[1] + 1)
    return tuple(counts[key] for key in sorted(counts))


def _child_profiles(values: tuple[Any, ...], stars: Sequence[Sequence[int]]) -> tuple[Any, ...]:
    return tuple(_profile(values, star) for star in stars)


def _vertex_permutation_from_ground(
    canonical_vertex_subsets: Sequence[Sequence[int]],
    ground_permutation: Sequence[int],
) -> tuple[int, ...]:
    index = {tuple(subset): position for position, subset in enumerate(canonical_vertex_subsets)}
    if len(index) != len(canonical_vertex_subsets):
        raise ValueError("certified Johnson vertex family contains duplicates")
    out: list[int] = []
    for subset in canonical_vertex_subsets:
        image = tuple(sorted(ground_permutation[point] for point in subset))
        target = index.get(image)
        if target is None:
            raise ValueError("ground permutation does not induce the certified Johnson vertex family")
        out.append(target)
    if len(set(out)) != len(out):
        raise ValueError("induced Johnson action is not a permutation")
    return tuple(out)


def _validate_reduction(
    evidence: Any,
    *,
    johnson_ground_size: int,
    johnson_subset_size: int,
    embedding: Sequence[Sequence[int]],
    ambient_generators: Sequence[Sequence[int]],
) -> JohnsonGroundRelationalReductionEvidence:
    if not isinstance(evidence, JohnsonGroundRelationalReductionEvidence):
        raise ValueError("reduction_evidence has the wrong public contract type")
    required_true = (
        "certified",
        "canonical",
        "exact",
        "progress_certified",
        "solution_transport_certified",
        "ambient_membership_transport_certified",
        "complement_ambiguity_handled",
    )
    for field in required_true:
        value = getattr(evidence, field)
        if type(value) is not bool or value is not True:
            raise ValueError(f"reduction_evidence.{field} must be literal true")
    if evidence.schema_version != 1 or evidence.status != "certified_johnson_ground_relational_reduction":
        raise ValueError("reduction_evidence schema/status mismatch")
    if not _SHA256_RE.fullmatch(evidence.reduction_identity):
        raise ValueError("reduction_evidence has a malformed reduction identity")
    if not replay_johnson_ground_relational_reduction(
        evidence,
        johnson_ground_size=johnson_ground_size,
        johnson_subset_size=johnson_subset_size,
        embedding=embedding,
        ambient_generators=ambient_generators,
    ):
        raise ValueError("rev287 reduction replay failed")
    return evidence


def certify_johnson_child_semantic_reduction(
    *,
    reduction_evidence: JohnsonGroundRelationalReductionEvidence,
    johnson_ground_size: int,
    johnson_subset_size: int,
    embedding: Sequence[Sequence[int]],
    ambient_generators: Sequence[Sequence[int]],
    parent_source_values: Sequence[Any],
    parent_target_values: Sequence[Any],
) -> JohnsonChildSemanticBinding:
    """Build a replay-stable unary child projection from a certified J(v,k) relation.

    The value of a ground point is the multiset of frozen parent colors on the
    Johnson vertices incident with that point. This projection is equivariant:
    every parent transporter represented by the certified ground action is also
    a transporter of the child strings. The converse is deliberately *not*
    certified; equal incident-color profiles can forget higher-order structure.
    """

    try:
        v = _strict_int(johnson_ground_size, "johnson_ground_size")
        k = _strict_int(johnson_subset_size, "johnson_subset_size")
        evidence = _validate_reduction(
            reduction_evidence,
            johnson_ground_size=v,
            johnson_subset_size=k,
            embedding=embedding,
            ambient_generators=ambient_generators,
        )
        n = evidence.source_action_degree
        if evidence.johnson_ground_size != v or evidence.child_ground_size != v:
            raise ValueError("reduction_evidence child ground disagrees with caller ground")
        if evidence.johnson_subset_size != k:
            raise ValueError("reduction_evidence subset size disagrees with caller")
        if len(evidence.canonical_vertex_subsets) != n or len(evidence.canonical_ground_stars) != v:
            raise ValueError("reduction_evidence omits canonical Johnson incidence data")

        source = _normalize_parent_values(parent_source_values, degree=n, name="parent_source_values")
        target = _normalize_parent_values(parent_target_values, degree=n, name="parent_target_values")
        child_source = _child_profiles(source, evidence.canonical_ground_stars)
        child_target = _child_profiles(target, evidence.canonical_ground_stars)

        for index, raw_ground in enumerate(evidence.induced_ground_generators):
            ground = _normalize_permutation(raw_ground, degree=v, name=f"induced_ground_generators[{index}]")
            vertex = _vertex_permutation_from_ground(evidence.canonical_vertex_subsets, ground)
            moved_source = _child_profiles(_transport(source, vertex), evidence.canonical_ground_stars)
            moved_target = _child_profiles(_transport(target, vertex), evidence.canonical_ground_stars)
            if moved_source != _transport(child_source, ground):
                raise ValueError(f"source semantic projection is not equivariant for induced generator {index}")
            if moved_target != _transport(child_target, ground):
                raise ValueError(f"target semantic projection is not equivariant for induced generator {index}")

        parent_source_digest = _sha256(("parent_string_v1", source))
        parent_target_digest = _sha256(("parent_string_v1", target))
        child_source_digest = _sha256((PROFILE_KIND, child_source))
        child_target_digest = _sha256((PROFILE_KIND, child_target))
        m = len(evidence.induced_ground_generators)
        semantic_work_bound = evidence.construction_work_bound + (2 + 2 * m) * n * k + m * (n + v)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": STATUS,
            "profile_kind": PROFILE_KIND,
            "source_action_degree": n,
            "child_ground_size": v,
            "johnson_subset_size": k,
            "reduction_identity": evidence.reduction_identity,
            "parent_source_digest": parent_source_digest,
            "parent_target_digest": parent_target_digest,
            "child_source_digest": child_source_digest,
            "child_target_digest": child_target_digest,
            "child_source_values": child_source,
            "child_target_values": child_target,
            "semantic_work_bound": semantic_work_bound,
            "parent_to_child_transport_certified": True,
            "child_to_parent_transport_certified": False,
            "parent_solution_equivalence_certified": False,
        }
        identity = _sha256(payload)
    except (ValueError, TypeError, OverflowError) as exc:
        n = getattr(reduction_evidence, "source_action_degree", 0)
        v = johnson_ground_size if type(johnson_ground_size) is int else 0
        k = johnson_subset_size if type(johnson_subset_size) is int else 0
        return _fail(str(exc), n=n if type(n) is int else 0, v=v, k=k)

    return JohnsonChildSemanticBinding(
        SCHEMA_VERSION,
        STATUS,
        True,
        True,
        True,
        True,
        False,
        False,
        n,
        v,
        k,
        PROFILE_KIND,
        evidence.reduction_identity,
        parent_source_digest,
        parent_target_digest,
        child_source_digest,
        child_target_digest,
        child_source,
        child_target,
        semantic_work_bound,
        identity,
        "incident parent-color multisets give a deterministic replay-stable unary ground projection; every certified ground-action parent transporter preserves the projection, but the converse and full parent/child solution equivalence remain deliberately uncertified",
    )


def replay_johnson_child_semantic_reduction(
    binding: JohnsonChildSemanticBinding,
    **kwargs: Any,
) -> bool:
    if not isinstance(binding, JohnsonChildSemanticBinding) or not binding.certified:
        return False
    replay = certify_johnson_child_semantic_reduction(**kwargs)
    return bool(
        replay.certified
        and replay == binding
        and _SHA256_RE.fullmatch(binding.binding_identity)
        and binding.parent_to_child_transport_certified is True
        and binding.child_to_parent_transport_certified is False
        and binding.parent_solution_equivalence_certified is False
    )


def verify_ground_candidate_parent_transport(
    binding: JohnsonChildSemanticBinding,
    *,
    reduction_evidence: JohnsonGroundRelationalReductionEvidence,
    johnson_ground_size: int,
    johnson_subset_size: int,
    embedding: Sequence[Sequence[int]],
    ambient_generators: Sequence[Sequence[int]],
    parent_source_values: Sequence[Any],
    parent_target_values: Sequence[Any],
    ground_permutation: Sequence[int],
) -> bool:
    """Exactly filter one ground candidate against the original parent string."""

    kwargs = {
        "reduction_evidence": reduction_evidence,
        "johnson_ground_size": johnson_ground_size,
        "johnson_subset_size": johnson_subset_size,
        "embedding": embedding,
        "ambient_generators": ambient_generators,
        "parent_source_values": parent_source_values,
        "parent_target_values": parent_target_values,
    }
    if not replay_johnson_child_semantic_reduction(binding, **kwargs):
        return False
    try:
        ground = _normalize_permutation(ground_permutation, degree=binding.child_ground_size, name="ground_permutation")
        if _transport(binding.child_source_values, ground) != binding.child_target_values:
            return False
        source = _normalize_parent_values(parent_source_values, degree=binding.source_action_degree, name="parent_source_values")
        target = _normalize_parent_values(parent_target_values, degree=binding.source_action_degree, name="parent_target_values")
        vertex = _vertex_permutation_from_ground(reduction_evidence.canonical_vertex_subsets, ground)
        return _transport(source, vertex) == target
    except (ValueError, TypeError, OverflowError):
        return False


__all__ = [
    "JohnsonChildSemanticBinding",
    "certify_johnson_child_semantic_reduction",
    "replay_johnson_child_semantic_reduction",
    "verify_ground_candidate_parent_transport",
]
