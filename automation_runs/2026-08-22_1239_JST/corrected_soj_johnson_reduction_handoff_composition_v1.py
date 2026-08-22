from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from itertools import combinations
from math import comb, isfinite, lgamma, log, log2
from typing import Any, Sequence

SCHEMA_VERSION = 1
REDUCTION_STATUS = "certified_johnson_ground_relational_reduction"
GROUND_CAP_STATUS = "undetermined_johnson_ground_cap"
GROUND_CAP_OPERATION = "primitive_johnson_ground_cap"
HANDOFF_STATUS = "certified_corrected_soj_larger_ground_recursive_handoff"
VALIDATION_STATUS = "certified_quasipolynomial_recurrence"
COMPOSITION_STATUS = "certified_johnson_reduction_handoff_composition"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class JohnsonReductionConstructionSnapshot:
    schema_version: int
    status: str
    certified: bool
    canonical: bool
    exact: bool
    progress_certified: bool
    solution_transport_certified: bool
    ambient_membership_transport_certified: bool
    complement_ambiguity_handled: bool
    source_action_degree: int
    johnson_ground_size: int
    johnson_subset_size: int
    child_ground_size: int
    multiplicative_cost: float
    max_multiplicative_cost: float
    reduction_identity: str
    generator_count: int
    construction_work_bound: int
    vertex_subset_digest: str
    ground_star_digest: str
    ground_generator_digest: str
    construction_digest: str


@dataclass(frozen=True)
class JohnsonRecursiveHandoffSnapshot:
    schema_version: int
    status: str
    certified: bool
    handoff_digest: str
    reduction_identity: str
    root_n: int
    source_action_degree: int
    child_ground_size: int
    charged_log2_reduction_cost: float
    accounting_tree_digest: str
    validation_status: str
    validation_log2_work_bound: float
    validation_allowed_log2_work: float
    validation_nodes_checked: int
    validation_max_depth: int
    shrink_fraction: float
    handoff_snapshot_digest: str


@dataclass(frozen=True)
class JohnsonReductionHandoffCompositionCertificate:
    schema_version: int
    status: str
    certified: bool
    construction: JohnsonReductionConstructionSnapshot | None
    handoff: JohnsonRecursiveHandoffSnapshot | None
    composition_digest: str
    reason: str


@dataclass(frozen=True)
class _AccountingResult:
    payload: dict[str, Any]
    digest: str
    log2_work_bound: float
    nodes_checked: int
    max_depth: int


def _fail(
    reason: str,
    *,
    construction: JohnsonReductionConstructionSnapshot | None = None,
    handoff: JohnsonRecursiveHandoffSnapshot | None = None,
    status: str = "johnson_reduction_handoff_composition_not_certified",
) -> JohnsonReductionHandoffCompositionCertificate:
    return JohnsonReductionHandoffCompositionCertificate(
        SCHEMA_VERSION,
        status,
        False,
        construction,
        handoff,
        "",
        reason,
    )


def _field(obj: Any, name: str) -> Any:
    attribute = name.rsplit(".", 1)[-1]
    if not hasattr(obj, attribute):
        raise ValueError(f"missing required field {name!r}")
    return getattr(obj, attribute)


def _strict_bool(obj: Any, name: str) -> bool:
    value = _field(obj, name)
    if type(value) is not bool:
        raise ValueError(f"{name} must be a strict boolean")
    return value


def _strict_int(obj: Any, name: str) -> int:
    value = _field(obj, name)
    if type(value) is not int:
        raise ValueError(f"{name} must be a strict integer")
    return value


def _strict_text(obj: Any, name: str) -> str:
    value = _field(obj, name)
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    return value


def _strict_real(obj: Any, name: str) -> float:
    value = _field(obj, name)
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"{name} must be a finite real number")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{name} must be a finite real number")
    return value


def _strict_sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _normalize_increasing_int_tuple(
    raw: Any,
    *,
    name: str,
    length: int | None = None,
    upper: int,
) -> tuple[int, ...]:
    seq = _strict_sequence(raw, name)
    if length is not None and len(seq) != length:
        raise ValueError(f"{name} must have length {length}")
    values: list[int] = []
    for index, value in enumerate(seq):
        if type(value) is not int:
            raise ValueError(f"{name}[{index}] must be a strict integer")
        if not 0 <= value < upper:
            raise ValueError(f"{name}[{index}] is outside the certified domain")
        values.append(value)
    result = tuple(values)
    if result != tuple(sorted(result)) or len(set(result)) != len(result):
        raise ValueError(f"{name} must be strictly increasing")
    return result


def _normalize_permutation(raw: Any, *, name: str, degree: int) -> tuple[int, ...]:
    seq = _strict_sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong permutation degree")
    values: list[int] = []
    for index, value in enumerate(seq):
        if type(value) is not int:
            raise ValueError(f"{name}[{index}] must be a strict integer")
        if not 0 <= value < degree:
            raise ValueError(f"{name}[{index}] is outside the permutation domain")
        values.append(value)
    result = tuple(values)
    if len(set(result)) != degree:
        raise ValueError(f"{name} is not a permutation")
    return result


def _construction_snapshot(evidence: Any) -> JohnsonReductionConstructionSnapshot:
    schema_version = _strict_int(evidence, "schema_version")
    status = _strict_text(evidence, "status")
    certified = _strict_bool(evidence, "certified")
    canonical = _strict_bool(evidence, "canonical")
    exact = _strict_bool(evidence, "exact")
    progress = _strict_bool(evidence, "progress_certified")
    solution_transport = _strict_bool(evidence, "solution_transport_certified")
    membership_transport = _strict_bool(evidence, "ambient_membership_transport_certified")
    complement = _strict_bool(evidence, "complement_ambiguity_handled")
    n = _strict_int(evidence, "source_action_degree")
    v = _strict_int(evidence, "johnson_ground_size")
    k = _strict_int(evidence, "johnson_subset_size")
    child = _strict_int(evidence, "child_ground_size")
    cost = _strict_real(evidence, "multiplicative_cost")
    max_cost = _strict_real(evidence, "max_multiplicative_cost")
    reduction_identity = _strict_text(evidence, "reduction_identity")
    work_bound = _strict_int(evidence, "construction_work_bound")

    if schema_version != SCHEMA_VERSION:
        raise ValueError("construction evidence schema_version is unsupported")
    if status != REDUCTION_STATUS:
        raise ValueError("construction evidence has the wrong reduction status")
    if not certified:
        raise ValueError("construction evidence is not certified")
    if not (canonical and exact and progress):
        raise ValueError("construction evidence must be canonical, exact, and progress-certified")
    if not (solution_transport and membership_transport):
        raise ValueError("construction evidence must certify solution and ambient-membership transport")
    if not complement:
        raise ValueError("construction evidence must handle Johnson complement ambiguity explicitly")
    if v < 4 or not 2 <= k <= v - 2:
        raise ValueError("construction evidence has malformed Johnson parameters")
    if n != comb(v, k):
        raise ValueError("construction source degree is not C(v,k)")
    if child != v or n <= child:
        raise ValueError("construction evidence does not certify a strict J(v,k)-to-ground reduction")
    if cost < 1.0 or max_cost < 1.0 or cost > max_cost:
        raise ValueError("construction multiplicative cost is outside its certified bound")
    if not _SHA256_RE.fullmatch(reduction_identity):
        raise ValueError("construction reduction_identity must be a canonical sha256 digest")

    raw_subsets = _strict_sequence(
        _field(evidence, "canonical_vertex_subsets"),
        "canonical_vertex_subsets",
    )
    if len(raw_subsets) != n:
        raise ValueError("canonical_vertex_subsets length differs from source_action_degree")
    subsets = tuple(
        _normalize_increasing_int_tuple(
            raw,
            name=f"canonical_vertex_subsets[{index}]",
            length=k,
            upper=v,
        )
        for index, raw in enumerate(raw_subsets)
    )
    expected_subsets = set(combinations(range(v), k))
    if len(set(subsets)) != n or set(subsets) != expected_subsets:
        raise ValueError("canonical_vertex_subsets is not a complete copy of J(v,k)")

    raw_stars = _strict_sequence(
        _field(evidence, "canonical_ground_stars"),
        "canonical_ground_stars",
    )
    if len(raw_stars) != v:
        raise ValueError("canonical_ground_stars length differs from johnson_ground_size")
    stars = tuple(
        _normalize_increasing_int_tuple(
            raw,
            name=f"canonical_ground_stars[{index}]",
            upper=n,
        )
        for index, raw in enumerate(raw_stars)
    )
    expected_stars = tuple(
        tuple(index for index, subset in enumerate(subsets) if point in subset)
        for point in range(v)
    )
    if stars != expected_stars:
        raise ValueError(
            "canonical_ground_stars does not exactly match canonical_vertex_subsets incidence"
        )

    raw_generators = _strict_sequence(
        _field(evidence, "induced_ground_generators"),
        "induced_ground_generators",
    )
    generators = tuple(
        _normalize_permutation(
            raw,
            name=f"induced_ground_generators[{index}]",
            degree=v,
        )
        for index, raw in enumerate(raw_generators)
    )
    generator_count = len(generators)
    expected_work = (2 + 2 * generator_count) * n * k + generator_count * n + v
    if work_bound != expected_work:
        raise ValueError(
            "construction_work_bound does not match the certified construction trace"
        )

    vertex_digest = _sha256(subsets)
    star_digest = _sha256(stars)
    generator_digest = _sha256(generators)
    payload = {
        "schema_version": schema_version,
        "status": status,
        "certified": certified,
        "canonical": canonical,
        "exact": exact,
        "progress_certified": progress,
        "solution_transport_certified": solution_transport,
        "ambient_membership_transport_certified": membership_transport,
        "complement_ambiguity_handled": complement,
        "source_action_degree": n,
        "johnson_ground_size": v,
        "johnson_subset_size": k,
        "child_ground_size": child,
        "multiplicative_cost": cost,
        "max_multiplicative_cost": max_cost,
        "reduction_identity": reduction_identity,
        "generator_count": generator_count,
        "construction_work_bound": work_bound,
        "vertex_subset_digest": vertex_digest,
        "ground_star_digest": star_digest,
        "ground_generator_digest": generator_digest,
    }
    return JohnsonReductionConstructionSnapshot(
        schema_version,
        status,
        certified,
        canonical,
        exact,
        progress,
        solution_transport,
        membership_transport,
        complement,
        n,
        v,
        k,
        child,
        cost,
        max_cost,
        reduction_identity,
        generator_count,
        work_bound,
        vertex_digest,
        star_digest,
        generator_digest,
        _sha256(payload),
    )


def _log2_sum_exp(values: Sequence[float]) -> float:
    values = tuple(values)
    if not values:
        return 0.0
    top = max(values)
    return top + log2(sum(2.0 ** (value - top) for value in values))


def _log2_factorial(value: int) -> float:
    if value < 0:
        raise ValueError("factorial input must be nonnegative")
    return lgamma(value + 1) / log(2.0)


def _accounting_tree_snapshot(
    root: Any,
    *,
    shrink_fraction: float,
    polylog_power: int,
    max_nodes: int = 10000,
) -> _AccountingResult:
    active_ids: set[int] = set()
    visited_count = 0

    def rec(node: Any, path: str) -> _AccountingResult:
        nonlocal visited_count
        visited_count += 1
        if visited_count > max_nodes:
            raise ValueError("accounting tree exceeds the structural node limit")
        node_id = id(node)
        if node_id in active_ids:
            raise ValueError("accounting tree contains a cycle")
        active_ids.add(node_id)
        try:
            n = _strict_int(node, f"{path}.n")
            m = _strict_int(node, f"{path}.m")
            operation = _strict_text(node, f"{path}.operation_kind")
            canonical = _strict_bool(node, f"{path}.canonical")
            cost_certified = _strict_bool(node, f"{path}.cost_certified")
            local_cost = _strict_real(node, f"{path}.local_log2_cost_bound")
            terminal = _strict_bool(node, f"{path}.terminal_certified")
            reason = _strict_text(node, f"{path}.reason")
            children_raw = _strict_sequence(
                _field(node, "children"),
                f"{path}.children",
            )

            if n <= 0 or m <= 0 or m > n:
                raise ValueError(f"{path} requires 1 <= m <= n")
            if not canonical:
                raise ValueError(f"{path} is not canonical")
            if not cost_certified:
                raise ValueError(f"{path} lacks a certified local cost")
            if local_cost < 0.0:
                raise ValueError(f"{path} has a negative local log2 cost")
            if not children_raw:
                if not terminal:
                    raise ValueError(f"{path} is an uncertified accounting leaf")
                payload = {
                    "n": n,
                    "m": m,
                    "operation_kind": operation,
                    "canonical": canonical,
                    "cost_certified": cost_certified,
                    "local_log2_cost_bound": local_cost,
                    "children": [],
                    "terminal_certified": terminal,
                    "reason": reason,
                }
                return _AccountingResult(payload, _sha256(payload), local_cost, 1, 0)
            if terminal:
                raise ValueError(
                    f"{path} is terminal but also has recursive children"
                )

            threshold = max(1.0, log2(max(2, n)) ** polylog_power)
            child_payloads: list[dict[str, Any]] = []
            child_terms: list[float] = []
            nodes = 1
            depth = 0
            for index, edge in enumerate(children_raw):
                multiplicity = _strict_int(
                    edge,
                    f"{path}.children[{index}].multiplicity",
                )
                if multiplicity <= 0:
                    raise ValueError(
                        f"{path}.children[{index}] has nonpositive multiplicity"
                    )
                child = _field(edge, "node")
                child_result = rec(
                    child,
                    f"{path}.children[{index}].node",
                )
                child_n = child_result.payload["n"]
                child_m = child_result.payload["m"]
                if child_n > n or child_m > child_n:
                    raise ValueError(
                        f"{path}.children[{index}] increases a recurrence measure"
                    )
                if operation == "aux_shrink":
                    if child_m > shrink_fraction * m + 1e-12:
                        raise ValueError(
                            f"{path}.children[{index}] does not achieve auxiliary shrink"
                        )
                elif operation == "small_aux_reset":
                    if m > threshold + 1e-12:
                        raise ValueError(
                            f"{path} resets before the auxiliary measure is polylogarithmic"
                        )
                    if child_n > shrink_fraction * n + 1e-12:
                        raise ValueError(
                            f"{path}.children[{index}] does not achieve primary shrink"
                        )
                    if local_cost + 1e-12 < _log2_factorial(m):
                        raise ValueError(
                            f"{path} undercharges auxiliary enumeration"
                        )
                else:
                    raise ValueError(
                        f"{path} has an unknown nonterminal operation_kind"
                    )
                child_payloads.append(
                    {
                        "multiplicity": multiplicity,
                        "node": child_result.payload,
                    }
                )
                child_terms.append(
                    log2(multiplicity) + child_result.log2_work_bound
                )
                nodes += child_result.nodes_checked
                depth = max(depth, 1 + child_result.max_depth)

            payload = {
                "n": n,
                "m": m,
                "operation_kind": operation,
                "canonical": canonical,
                "cost_certified": cost_certified,
                "local_log2_cost_bound": local_cost,
                "children": child_payloads,
                "terminal_certified": terminal,
                "reason": reason,
            }
            work = local_cost + _log2_sum_exp(child_terms)
            return _AccountingResult(
                payload,
                _sha256(payload),
                work,
                nodes,
                depth,
            )
        finally:
            active_ids.remove(node_id)

    return rec(root, "accounting_root")


def _ground_cap_payload(
    ground: Any,
    construction: JohnsonReductionConstructionSnapshot,
) -> dict[str, Any]:
    payload = {
        "status": _strict_text(ground, "ground_cap.status"),
        "operation_kind": _strict_text(ground, "ground_cap.operation_kind"),
        "root_n": _strict_int(ground, "ground_cap.root_n"),
        "domain_size": _strict_int(ground, "ground_cap.domain_size"),
        "canonical": _strict_bool(ground, "ground_cap.canonical"),
        "exact": _strict_bool(ground, "ground_cap.exact"),
        "local_cost_certified": _strict_bool(
            ground,
            "ground_cap.local_cost_certified",
        ),
        "terminal_certified": _strict_bool(
            ground,
            "ground_cap.terminal_certified",
        ),
        "johnson_ground_size": _strict_int(
            ground,
            "ground_cap.johnson_ground_size",
        ),
        "johnson_subset_size": _strict_int(
            ground,
            "ground_cap.johnson_subset_size",
        ),
    }
    if (
        payload["status"] != GROUND_CAP_STATUS
        or payload["operation_kind"] != GROUND_CAP_OPERATION
    ):
        raise ValueError(
            "handoff ground_cap is not the unresolved primitive-Johnson ground-cap outcome"
        )
    if not payload["canonical"]:
        raise ValueError("handoff ground_cap is not canonical")
    if (
        payload["exact"]
        or payload["local_cost_certified"]
        or payload["terminal_certified"]
    ):
        raise ValueError(
            "handoff ground_cap improperly claims terminal exactness or cost certification"
        )
    if (
        payload["root_n"] <= 0
        or not 0 < payload["domain_size"] <= payload["root_n"]
    ):
        raise ValueError("handoff ground_cap has invalid root/domain measures")
    if payload["domain_size"] != construction.source_action_degree:
        raise ValueError(
            "handoff ground_cap domain_size differs from the construction source degree"
        )
    if payload["johnson_ground_size"] != construction.johnson_ground_size:
        raise ValueError(
            "handoff ground_cap Johnson ground differs from the construction"
        )
    if payload["johnson_subset_size"] != construction.johnson_subset_size:
        raise ValueError(
            "handoff ground_cap Johnson subset size differs from the construction"
        )
    if (
        comb(
            payload["johnson_ground_size"],
            payload["johnson_subset_size"],
        )
        != payload["domain_size"]
    ):
        raise ValueError(
            "handoff ground_cap parameters do not reconstruct its action degree"
        )
    return payload


def _reduction_payload(
    reduction: Any,
    construction: JohnsonReductionConstructionSnapshot,
) -> dict[str, Any]:
    payload = {
        "status": _strict_text(reduction, "handoff.reduction.status"),
        "canonical": _strict_bool(reduction, "handoff.reduction.canonical"),
        "exact": _strict_bool(reduction, "handoff.reduction.exact"),
        "progress_certified": _strict_bool(
            reduction,
            "handoff.reduction.progress_certified",
        ),
        "solution_transport_certified": _strict_bool(
            reduction,
            "handoff.reduction.solution_transport_certified",
        ),
        "ambient_membership_transport_certified": _strict_bool(
            reduction,
            "handoff.reduction.ambient_membership_transport_certified",
        ),
        "complement_ambiguity_handled": _strict_bool(
            reduction,
            "handoff.reduction.complement_ambiguity_handled",
        ),
        "source_action_degree": _strict_int(
            reduction,
            "handoff.reduction.source_action_degree",
        ),
        "johnson_ground_size": _strict_int(
            reduction,
            "handoff.reduction.johnson_ground_size",
        ),
        "johnson_subset_size": _strict_int(
            reduction,
            "handoff.reduction.johnson_subset_size",
        ),
        "child_ground_size": _strict_int(
            reduction,
            "handoff.reduction.child_ground_size",
        ),
        "multiplicative_cost": _strict_real(
            reduction,
            "handoff.reduction.multiplicative_cost",
        ),
        "max_multiplicative_cost": _strict_real(
            reduction,
            "handoff.reduction.max_multiplicative_cost",
        ),
        "reduction_identity": _strict_text(
            reduction,
            "handoff.reduction.reduction_identity",
        ),
    }
    expected = {
        "status": construction.status,
        "canonical": construction.canonical,
        "exact": construction.exact,
        "progress_certified": construction.progress_certified,
        "solution_transport_certified": construction.solution_transport_certified,
        "ambient_membership_transport_certified": (
            construction.ambient_membership_transport_certified
        ),
        "complement_ambiguity_handled": construction.complement_ambiguity_handled,
        "source_action_degree": construction.source_action_degree,
        "johnson_ground_size": construction.johnson_ground_size,
        "johnson_subset_size": construction.johnson_subset_size,
        "child_ground_size": construction.child_ground_size,
        "multiplicative_cost": construction.multiplicative_cost,
        "max_multiplicative_cost": construction.max_multiplicative_cost,
        "reduction_identity": construction.reduction_identity,
    }
    for name, expected_value in expected.items():
        if payload[name] != expected_value:
            raise ValueError(
                f"handoff reduction field {name!r} is not bound to the construction evidence"
            )
    return payload


def _handoff_snapshot(
    handoff: Any,
    construction: JohnsonReductionConstructionSnapshot,
    *,
    shrink_fraction: float,
    polylog_power: int,
    quasipoly_power: int,
    quasipoly_constant: float,
) -> JohnsonRecursiveHandoffSnapshot:
    schema_version = _strict_int(handoff, "schema_version")
    status = _strict_text(handoff, "status")
    certified = _strict_bool(handoff, "certified")
    charged_cost = _strict_real(handoff, "charged_log2_reduction_cost")
    handoff_digest = _strict_text(handoff, "handoff_digest")
    if schema_version != SCHEMA_VERSION:
        raise ValueError("handoff schema_version is unsupported")
    if status != HANDOFF_STATUS or not certified:
        raise ValueError(
            "handoff is not a certified larger-ground recursive handoff"
        )
    if not _SHA256_RE.fullmatch(handoff_digest):
        raise ValueError("handoff_digest must be a canonical sha256 digest")

    ground_obj = _field(handoff, "ground_cap")
    reduction_obj = _field(handoff, "reduction")
    ground_payload = _ground_cap_payload(ground_obj, construction)
    reduction_payload = _reduction_payload(reduction_obj, construction)

    expected_charge = log2(construction.max_multiplicative_cost)
    if abs(charged_cost - expected_charge) > 1e-12:
        raise ValueError(
            "handoff charged cost is not log2 of the construction cost bound"
        )

    accounting_root = _field(handoff, "accounting_root")
    accounting = _accounting_tree_snapshot(
        accounting_root,
        shrink_fraction=shrink_fraction,
        polylog_power=polylog_power,
    )
    root_payload = accounting.payload
    if root_payload["n"] != ground_payload["root_n"]:
        raise ValueError(
            "handoff accounting root does not preserve the original root measure"
        )
    if root_payload["m"] != construction.source_action_degree:
        raise ValueError(
            "handoff accounting root is not attached to the construction source degree"
        )
    if root_payload["operation_kind"] != "aux_shrink":
        raise ValueError("handoff accounting root must be an aux_shrink edge")
    if abs(root_payload["local_log2_cost_bound"] - charged_cost) > 1e-12:
        raise ValueError(
            "handoff accounting root charge differs from charged_log2_reduction_cost"
        )
    if (
        len(root_payload["children"]) != 1
        or root_payload["children"][0]["multiplicity"] != 1
    ):
        raise ValueError(
            "handoff accounting root must contain one multiplicity-one recursive child"
        )
    child_payload = root_payload["children"][0]["node"]
    if child_payload["n"] != ground_payload["root_n"]:
        raise ValueError(
            "handoff recursive child changes the original root measure"
        )
    if child_payload["m"] != construction.child_ground_size:
        raise ValueError(
            "handoff recursive child auxiliary measure differs from the constructed ground"
        )

    allowed = quasipoly_constant * (
        log2(max(2, root_payload["n"])) ** quasipoly_power
    )
    if accounting.log2_work_bound > allowed + 1e-9:
        raise ValueError(
            "independently replayed accounting exceeds the configured quasipolynomial envelope"
        )

    validation = _field(handoff, "validation")
    validation_status = _strict_text(
        validation,
        "handoff.validation.status",
    )
    validation_certified = _strict_bool(
        validation,
        "handoff.validation.certified",
    )
    validation_work = _strict_real(
        validation,
        "handoff.validation.log2_work_bound",
    )
    validation_allowed = _strict_real(
        validation,
        "handoff.validation.allowed_log2_work",
    )
    validation_nodes = _strict_int(
        validation,
        "handoff.validation.nodes_checked",
    )
    validation_depth = _strict_int(
        validation,
        "handoff.validation.max_depth",
    )
    _strict_text(validation, "handoff.validation.reason")
    if validation_status != VALIDATION_STATUS or not validation_certified:
        raise ValueError("handoff recurrence validation is not certified")
    if abs(validation_work - accounting.log2_work_bound) > 1e-9:
        raise ValueError(
            "handoff validation work bound disagrees with independent accounting replay"
        )
    if abs(validation_allowed - allowed) > 1e-9:
        raise ValueError(
            "handoff validation envelope disagrees with independent accounting replay"
        )
    if (
        validation_nodes != accounting.nodes_checked
        or validation_depth != accounting.max_depth
    ):
        raise ValueError(
            "handoff validation node/depth counts disagree with the accounting tree"
        )

    expected_handoff_digest = _sha256(
        {
            "schema_version": SCHEMA_VERSION,
            "ground_cap": ground_payload,
            "reduction": reduction_payload,
            "child_measure": [
                int(child_payload["n"]),
                int(child_payload["m"]),
            ],
            "child_operation_kind": str(child_payload["operation_kind"]),
            "charged_log2_reduction_cost": float(charged_cost),
            "shrink_fraction": float(shrink_fraction),
        }
    )
    if handoff_digest != expected_handoff_digest:
        raise ValueError(
            "handoff_digest does not replay from the bound construction and child"
        )

    snapshot_payload = {
        "schema_version": schema_version,
        "status": status,
        "certified": certified,
        "handoff_digest": handoff_digest,
        "reduction_identity": construction.reduction_identity,
        "root_n": ground_payload["root_n"],
        "source_action_degree": construction.source_action_degree,
        "child_ground_size": construction.child_ground_size,
        "charged_log2_reduction_cost": charged_cost,
        "accounting_tree_digest": accounting.digest,
        "validation_status": validation_status,
        "validation_log2_work_bound": validation_work,
        "validation_allowed_log2_work": validation_allowed,
        "validation_nodes_checked": validation_nodes,
        "validation_max_depth": validation_depth,
        "shrink_fraction": float(shrink_fraction),
    }
    return JohnsonRecursiveHandoffSnapshot(
        schema_version,
        status,
        certified,
        handoff_digest,
        construction.reduction_identity,
        ground_payload["root_n"],
        construction.source_action_degree,
        construction.child_ground_size,
        charged_cost,
        accounting.digest,
        validation_status,
        validation_work,
        validation_allowed,
        validation_nodes,
        validation_depth,
        float(shrink_fraction),
        _sha256(snapshot_payload),
    )


def certify_johnson_reduction_handoff_composition(
    construction_evidence: Any,
    recursive_handoff: Any,
    *,
    shrink_fraction: float = 0.9,
    polylog_power: int = 2,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> JohnsonReductionHandoffCompositionCertificate:
    """Certify that a Johnson reduction construction is the exact handoff input.

    The boundary is deliberately structural: it imports neither sibling module.
    It independently checks the complete J(v,k) incidence certificate, validates
    the recurrence-accounting tree, replays the rev291 handoff digest, and then
    binds both to one deterministic composition digest. It does not execute the
    recursive String Isomorphism child and does not claim global SOJ/GI closure.
    """
    if (
        type(shrink_fraction) not in (int, float)
        or type(shrink_fraction) is bool
    ):
        return _fail("shrink_fraction must be a finite real number")
    shrink_fraction = float(shrink_fraction)
    if not isfinite(shrink_fraction) or not 0.0 < shrink_fraction < 1.0:
        return _fail("shrink_fraction must lie in (0,1)")
    if type(polylog_power) is not int or polylog_power < 1:
        return _fail("polylog_power must be a positive strict integer")
    if type(quasipoly_power) is not int or quasipoly_power < 1:
        return _fail("quasipoly_power must be a positive strict integer")
    if (
        type(quasipoly_constant) not in (int, float)
        or type(quasipoly_constant) is bool
    ):
        return _fail(
            "quasipoly_constant must be a positive finite real number"
        )
    quasipoly_constant = float(quasipoly_constant)
    if not isfinite(quasipoly_constant) or quasipoly_constant <= 0.0:
        return _fail(
            "quasipoly_constant must be a positive finite real number"
        )

    try:
        construction = _construction_snapshot(construction_evidence)
    except (AttributeError, TypeError, ValueError) as exc:
        return _fail(str(exc))
    try:
        handoff = _handoff_snapshot(
            recursive_handoff,
            construction,
            shrink_fraction=shrink_fraction,
            polylog_power=polylog_power,
            quasipoly_power=quasipoly_power,
            quasipoly_constant=quasipoly_constant,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        return _fail(str(exc), construction=construction)

    composition_payload = {
        "schema_version": SCHEMA_VERSION,
        "status": COMPOSITION_STATUS,
        "construction_digest": construction.construction_digest,
        "reduction_identity": construction.reduction_identity,
        "handoff_digest": handoff.handoff_digest,
        "handoff_snapshot_digest": handoff.handoff_snapshot_digest,
        "accounting_tree_digest": handoff.accounting_tree_digest,
        "root_n": handoff.root_n,
        "source_action_degree": handoff.source_action_degree,
        "child_ground_size": handoff.child_ground_size,
        "shrink_fraction": handoff.shrink_fraction,
    }
    return JohnsonReductionHandoffCompositionCertificate(
        SCHEMA_VERSION,
        COMPOSITION_STATUS,
        True,
        construction,
        handoff,
        _sha256(composition_payload),
        "the complete Johnson-ground construction evidence is exactly the reduction consumed by the certified larger-ground recursive handoff; the handoff digest and full recurrence-accounting tree replay independently and bind to one deterministic composition certificate",
    )


def replay_johnson_reduction_handoff_composition(
    certificate: JohnsonReductionHandoffCompositionCertificate,
    construction_evidence: Any,
    recursive_handoff: Any,
    **kwargs: Any,
) -> bool:
    if (
        not isinstance(
            certificate,
            JohnsonReductionHandoffCompositionCertificate,
        )
        or not certificate.certified
    ):
        return False
    replay = certify_johnson_reduction_handoff_composition(
        construction_evidence,
        recursive_handoff,
        **kwargs,
    )
    return bool(
        replay.certified
        and replay == certificate
        and replay.composition_digest == certificate.composition_digest
    )


__all__ = [
    "JohnsonReductionConstructionSnapshot",
    "JohnsonRecursiveHandoffSnapshot",
    "JohnsonReductionHandoffCompositionCertificate",
    "certify_johnson_reduction_handoff_composition",
    "replay_johnson_reduction_handoff_composition",
]
