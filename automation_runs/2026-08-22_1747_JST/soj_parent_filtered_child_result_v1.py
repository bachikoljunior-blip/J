from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 1
SEMANTIC_STATUS = "certified_johnson_child_semantic_projection"
EXECUTION_STATUS = "certified_recursive_ground_s1_child_instance_execution"
CHILD_NONEMPTY_STATUS = "exact_recursive_ground_coset"
CHILD_EMPTY_STATUS = "exact_empty_recursive_ground_coset"
OUTPUT_NONEMPTY_STATUS = "exact_parent_filtered_ground_coset"
OUTPUT_EMPTY_STATUS = "exact_empty_parent_filtered_ground_coset"
PROFILE_KIND = "incident_parent_color_multiset_v1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ParentFilteredGroundResult:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    reduction_identity: str
    semantic_binding_identity: str
    child_instance_identity: str
    child_result_identity: str
    action_degree: int
    candidate_count: int
    accepted_count: int
    representative: tuple[int, ...] | None
    parent_stabilizer_elements: tuple[tuple[int, ...], ...]
    work_bound: int
    result_identity: str
    reason: str


def _fail(reason: str) -> ParentFilteredGroundResult:
    return ParentFilteredGroundResult(
        SCHEMA_VERSION,
        "parent_filtered_ground_result_not_certified",
        False,
        False,
        False,
        "",
        "",
        "",
        "",
        0,
        0,
        0,
        None,
        (),
        0,
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
    value = _field(obj, name)
    if type(value) is not bool or value is not True:
        raise ValueError(f"{name} must be literal true")


def _strict_false(obj: Any, name: str) -> None:
    value = _field(obj, name)
    if type(value) is not bool or value is not False:
        raise ValueError(f"{name} must be literal false")


def _strict_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be a strict integer >= {minimum}")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


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
        out: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{path} dictionary keys must be strings")
            out[key] = _normalize_json(item, f"{path}.{key}")
        return out
    raise ValueError(f"{path} is not replay-stable JSON data")


def _normalize_permutation(raw: Any, *, degree: int, name: str) -> tuple[int, ...]:
    seq = _sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong degree")
    out = tuple(_strict_int(x, f"{name}[{i}]", minimum=0) for i, x in enumerate(seq))
    if any(x >= degree for x in out) or len(set(out)) != degree:
        raise ValueError(f"{name} is not a permutation of 0..{degree - 1}")
    return out


def _identity(n: int) -> tuple[int, ...]:
    return tuple(range(n))


def _compose(p: tuple[int, ...], q: tuple[int, ...]) -> tuple[int, ...]:
    if len(p) != len(q):
        raise ValueError("permutation degree mismatch")
    return tuple(q[p[i]] for i in range(len(p)))


def _inverse(p: tuple[int, ...]) -> tuple[int, ...]:
    out = [0] * len(p)
    for i, j in enumerate(p):
        out[j] = i
    return tuple(out)


def _transport(values: Sequence[Any], permutation: Sequence[int]) -> tuple[Any, ...]:
    if len(values) != len(permutation):
        raise ValueError("transport dimension mismatch")
    out: list[Any] = [None] * len(values)
    for source, target in enumerate(permutation):
        out[target] = values[source]
    return tuple(out)


def _enumerate_group(
    generators: Sequence[Sequence[int]],
    *,
    degree: int,
    cap: int,
    name: str,
) -> tuple[tuple[int, ...], ...]:
    cap = _strict_int(cap, "max_group_elements", minimum=1)
    gens = tuple(
        _normalize_permutation(raw, degree=degree, name=f"{name}[{index}]")
        for index, raw in enumerate(_sequence(generators, name))
    )
    if not gens:
        gens = (_identity(degree),)
    steps = tuple(sorted(set(gens + tuple(_inverse(g) for g in gens))))
    seen = {_identity(degree)}
    queue = [_identity(degree)]
    while queue:
        current = queue.pop(0)
        for step in steps:
            nxt = _compose(current, step)
            if nxt in seen:
                continue
            if len(seen) >= cap:
                raise ValueError(f"{name} generated group exceeds explicit cap {cap}")
            seen.add(nxt)
            queue.append(nxt)
    return tuple(sorted(seen))


def _normalize_parent_values(values: Any, *, degree: int, name: str) -> tuple[Any, ...]:
    seq = _sequence(values, name)
    if len(seq) != degree:
        raise ValueError(f"{name} length mismatch")
    return tuple(_freeze_value(value, f"{name}[{i}]") for i, value in enumerate(seq))


def _profile(values: tuple[Any, ...], star: Sequence[int]) -> tuple[Any, ...]:
    counts: dict[bytes, tuple[Any, int]] = {}
    for vertex in star:
        token = values[vertex]
        key = _canonical_bytes(token)
        previous = counts.get(key)
        counts[key] = (token, 1 if previous is None else previous[1] + 1)
    return tuple(counts[key] for key in sorted(counts))


def _canonical_vertices(raw: Any, *, v: int, k: int, n: int) -> tuple[tuple[int, ...], ...]:
    seq = _sequence(raw, "canonical_vertex_subsets")
    vertices: list[tuple[int, ...]] = []
    for index, item in enumerate(seq):
        subset_raw = _sequence(item, f"canonical_vertex_subsets[{index}]")
        subset = tuple(_strict_int(x, f"canonical_vertex_subsets[{index}]", minimum=0) for x in subset_raw)
        if len(subset) != k or tuple(sorted(subset)) != subset or len(set(subset)) != k or any(x >= v for x in subset):
            raise ValueError("canonical_vertex_subsets contains a malformed k-subset")
        vertices.append(subset)
    expected = tuple(combinations(range(v), k))
    if len(vertices) != n or tuple(vertices) != expected:
        raise ValueError("canonical_vertex_subsets must be the complete canonical J(v,k) family")
    return tuple(vertices)


def _ground_stars(vertices: Sequence[Sequence[int]], v: int) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(index for index, subset in enumerate(vertices) if point in subset)
        for point in range(v)
    )


def _vertex_permutation(
    vertices: Sequence[Sequence[int]],
    ground_permutation: tuple[int, ...],
) -> tuple[int, ...]:
    index = {tuple(subset): i for i, subset in enumerate(vertices)}
    out = tuple(
        index[tuple(sorted(ground_permutation[x] for x in subset))]
        for subset in vertices
    )
    if len(set(out)) != len(out):
        raise ValueError("ground permutation did not induce a Johnson vertex permutation")
    return out


def _validate_semantic_binding(
    binding: Any,
    *,
    canonical_vertex_subsets: Any,
    parent_source_values: Any,
    parent_target_values: Any,
) -> dict[str, Any]:
    if _field(binding, "schema_version") != SCHEMA_VERSION or _field(binding, "status") != SEMANTIC_STATUS:
        raise ValueError("semantic binding schema/status mismatch")
    for name in ("certified", "canonical", "replay_stable", "parent_to_child_transport_certified"):
        _strict_true(binding, name)
    for name in ("child_to_parent_transport_certified", "parent_solution_equivalence_certified"):
        _strict_false(binding, name)
    n = _strict_int(_field(binding, "source_action_degree"), "source_action_degree", minimum=1)
    v = _strict_int(_field(binding, "child_ground_size"), "child_ground_size", minimum=4)
    k = _strict_int(_field(binding, "johnson_subset_size"), "johnson_subset_size", minimum=2)
    if k > v - 2 or n != comb(v, k) or n <= v:
        raise ValueError("semantic binding Johnson dimensions are inconsistent or non-shrinking")
    if _field(binding, "profile_kind") != PROFILE_KIND:
        raise ValueError("semantic binding profile kind mismatch")
    reduction_identity = _field(binding, "reduction_identity")
    if not isinstance(reduction_identity, str) or _SHA256_RE.fullmatch(reduction_identity) is None:
        raise ValueError("semantic reduction_identity is malformed")
    vertices = _canonical_vertices(canonical_vertex_subsets, v=v, k=k, n=n)
    source = _normalize_parent_values(parent_source_values, degree=n, name="parent_source_values")
    target = _normalize_parent_values(parent_target_values, degree=n, name="parent_target_values")
    stars = _ground_stars(vertices, v)
    expected_child_source = tuple(_profile(source, star) for star in stars)
    expected_child_target = tuple(_profile(target, star) for star in stars)
    child_source = tuple(_field(binding, "child_source_values"))
    child_target = tuple(_field(binding, "child_target_values"))
    if _canonical_bytes(child_source) != _canonical_bytes(expected_child_source):
        raise ValueError("semantic child source is not the exact incident-color profile of the parent source")
    if _canonical_bytes(child_target) != _canonical_bytes(expected_child_target):
        raise ValueError("semantic child target is not the exact incident-color profile of the parent target")
    parent_source_digest = _sha256(("parent_string_v1", source))
    parent_target_digest = _sha256(("parent_string_v1", target))
    child_source_digest = _sha256((PROFILE_KIND, child_source))
    child_target_digest = _sha256((PROFILE_KIND, child_target))
    for name, expected in (
        ("parent_source_digest", parent_source_digest),
        ("parent_target_digest", parent_target_digest),
        ("child_source_digest", child_source_digest),
        ("child_target_digest", child_target_digest),
    ):
        if _field(binding, name) != expected:
            raise ValueError(f"semantic {name} drift")
    semantic_work_bound = _strict_int(_field(binding, "semantic_work_bound"), "semantic_work_bound", minimum=1)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": SEMANTIC_STATUS,
        "profile_kind": PROFILE_KIND,
        "source_action_degree": n,
        "child_ground_size": v,
        "johnson_subset_size": k,
        "reduction_identity": reduction_identity,
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
    binding_identity = _field(binding, "binding_identity")
    if binding_identity != _sha256(payload):
        raise ValueError("semantic binding identity replay failed")
    return {
        "n": n,
        "v": v,
        "k": k,
        "vertices": vertices,
        "source": source,
        "target": target,
        "child_source": child_source,
        "child_target": child_target,
        "reduction_identity": reduction_identity,
        "binding_identity": binding_identity,
        "semantic_work_bound": semantic_work_bound,
    }


def _validate_child_execution(
    execution: Any,
    *,
    semantic: dict[str, Any],
    execution_context: Mapping[str, Any],
    max_group_elements: int,
) -> dict[str, Any]:
    if _field(execution, "schema_version") != SCHEMA_VERSION or _field(execution, "status") != EXECUTION_STATUS:
        raise ValueError("child execution schema/status mismatch")
    for name in ("certified", "exact", "complete"):
        _strict_true(execution, name)
    _strict_false(execution, "parent_child_semantic_transport_certified")
    v = semantic["v"]
    if _field(execution, "action_degree") != v:
        raise ValueError("child execution action degree mismatch")
    if _field(execution, "reduction_identity") != semantic["reduction_identity"]:
        raise ValueError("child execution reduction identity mismatch")

    ctx = execution_context
    n = _strict_int(_field(ctx, "source_action_degree"), "execution_context.source_action_degree", minimum=1)
    k = _strict_int(_field(ctx, "subset_size"), "execution_context.subset_size", minimum=1)
    if n != semantic["n"] or k != semantic["k"]:
        raise ValueError("child execution context disagrees with semantic Johnson dimensions")
    raw_gens = _field(ctx, "induced_ground_generators")
    gens = tuple(
        _normalize_permutation(g, degree=v, name=f"execution_context.induced_ground_generators[{i}]")
        for i, g in enumerate(_sequence(raw_gens, "execution_context.induced_ground_generators"))
    )
    ctx_source = tuple(_normalize_json(x, f"execution_context.child_source_values[{i}]") for i, x in enumerate(_sequence(_field(ctx, "child_source_values"), "execution_context.child_source_values")))
    ctx_target = tuple(_normalize_json(x, f"execution_context.child_target_values[{i}]") for i, x in enumerate(_sequence(_field(ctx, "child_target_values"), "execution_context.child_target_values")))
    if len(ctx_source) != v or len(ctx_target) != v:
        raise ValueError("child execution context string length mismatch")
    if _canonical_bytes(ctx_source) != _canonical_bytes(semantic["child_source"]):
        raise ValueError("executed child source is not the semantic projection")
    if _canonical_bytes(ctx_target) != _canonical_bytes(semantic["child_target"]):
        raise ValueError("executed child target is not the semantic projection")
    root_n = _strict_int(_field(ctx, "original_root_n"), "execution_context.original_root_n", minimum=1)
    if root_n < n:
        raise ValueError("execution original_root_n does not dominate parent action degree")
    resources_raw = _field(ctx, "resources")
    resources: dict[str, int] = {}
    for name, minimum in (
        ("polylog_power", 1),
        ("max_explicit_degree", 1),
        ("group_order_poly_power", 1),
        ("max_group_order", 1),
        ("max_partition_states", 1),
        ("max_recognition_nodes", 1),
        ("max_depth", 0),
    ):
        resources[name] = _strict_int(_field(resources_raw, name), f"execution_context.resources.{name}", minimum=minimum)

    result = _field(execution, "child_result")
    if result is None:
        raise ValueError("certified child execution omitted child_result")
    if _field(result, "schema_version") != SCHEMA_VERSION:
        raise ValueError("child result schema mismatch")
    for name in ("exact", "complete", "canonical", "ambient_membership_certified"):
        _strict_true(result, name)
    if _field(result, "action_degree") != v or _field(result, "reduction_identity") != semantic["reduction_identity"]:
        raise ValueError("child result dimension/reduction mismatch")
    status = _field(result, "status")
    representative_raw = _field(result, "representative")
    stabilizer_raw = _field(result, "stabilizer_generators")
    if status == CHILD_EMPTY_STATUS:
        if representative_raw is not None or tuple(stabilizer_raw) != ():
            raise ValueError("exact-empty child result must have no representative or stabilizer generators")
        representative = None
        stabilizer_generators: tuple[tuple[int, ...], ...] = ()
    elif status == CHILD_NONEMPTY_STATUS:
        representative = _normalize_permutation(representative_raw, degree=v, name="child_result.representative")
        stabilizer_generators = tuple(
            _normalize_permutation(g, degree=v, name=f"child_result.stabilizer_generators[{i}]")
            for i, g in enumerate(_sequence(stabilizer_raw, "child_result.stabilizer_generators"))
        )
        if tuple(sorted(set(stabilizer_generators))) != stabilizer_generators:
            raise ValueError("child stabilizer generators must be canonical sorted unique")
    else:
        raise ValueError("child result status mismatch")

    result_payload = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "exact": True,
        "complete": True,
        "canonical": True,
        "ambient_membership_certified": True,
        "action_degree": v,
        "reduction_identity": semantic["reduction_identity"],
        "representative": representative,
        "stabilizer_generators": stabilizer_generators,
    }
    result_identity = _field(result, "result_identity")
    if result_identity != _sha256(result_payload):
        raise ValueError("child result identity replay failed")

    child_instance_payload = {
        "schema_version": SCHEMA_VERSION,
        "scope": "corrected-soj-recursive-ground-s1-child-instance-v1",
        "reduction_identity": semantic["reduction_identity"],
        "source_action_degree": n,
        "ground_size": v,
        "subset_size": k,
        "induced_ground_generators": gens,
        "child_source_values": ctx_source,
        "child_target_values": ctx_target,
        "original_root_n": root_n,
        "resources": resources,
        "child_result_identity": result_identity,
    }
    child_instance_identity = _field(execution, "child_instance_identity")
    if child_instance_identity != _sha256(child_instance_payload):
        raise ValueError("child instance identity replay failed")

    ambient = _enumerate_group(gens, degree=v, cap=max_group_elements, name="induced_ground_generators")
    exact_child = tuple(
        g for g in ambient
        if _transport(ctx_source, g) == ctx_target
    )
    if representative is None:
        snapshot_child: tuple[tuple[int, ...], ...] = ()
    else:
        subgroup = _enumerate_group(
            stabilizer_generators or (_identity(v),),
            degree=v,
            cap=max_group_elements,
            name="child_stabilizer_generators",
        )
        snapshot_child = tuple(sorted({_compose(representative, h) for h in subgroup}))
    if tuple(sorted(exact_child)) != tuple(sorted(snapshot_child)):
        raise ValueError("child snapshot is not the exact child transporter set in the certified induced-ground group")
    return {
        "ambient": ambient,
        "child_candidates": tuple(sorted(snapshot_child)),
        "child_instance_identity": child_instance_identity,
        "child_result_identity": result_identity,
    }


def certify_parent_filtered_child_result(
    semantic_binding: Any,
    child_execution: Any,
    *,
    execution_context: Mapping[str, Any],
    canonical_vertex_subsets: Sequence[Sequence[int]],
    parent_source_values: Sequence[Any],
    parent_target_values: Sequence[Any],
    max_group_elements: int = 4096,
) -> ParentFilteredGroundResult:
    """Exact bounded filter of a semantic child result against the original parent Johnson string.

    This adapter intentionally does not trust the one-way child projection as an
    equivalence. It structurally replays the rev1900-shaped profile/hash contract,
    structurally replays the rev1700-shaped child result/instance identities, and
    independently enumerates the certified induced-ground group under an explicit
    cap to verify that the child snapshot is exact. It then checks every child
    transporter on all parent Johnson vertices.

    Certification therefore fails closed beyond the explicit group cap. The
    successful result is exact only for the represented Johnson-ground action; it
    does not lift back to any pre-Johnson/original domain and does not close
    corrected Split-or-Johnson.
    """
    try:
        cap = _strict_int(max_group_elements, "max_group_elements", minimum=1)
        semantic = _validate_semantic_binding(
            semantic_binding,
            canonical_vertex_subsets=canonical_vertex_subsets,
            parent_source_values=parent_source_values,
            parent_target_values=parent_target_values,
        )
        execution = _validate_child_execution(
            child_execution,
            semantic=semantic,
            execution_context=execution_context,
            max_group_elements=cap,
        )
        accepted: list[tuple[int, ...]] = []
        for candidate in execution["child_candidates"]:
            vertex = _vertex_permutation(semantic["vertices"], candidate)
            if _transport(semantic["source"], vertex) == semantic["target"]:
                accepted.append(candidate)
        accepted_set = tuple(sorted(set(accepted)))
        candidate_count = len(execution["child_candidates"])
        if not accepted_set:
            status = OUTPUT_EMPTY_STATUS
            representative = None
            parent_stabilizer_elements: tuple[tuple[int, ...], ...] = ()
        else:
            status = OUTPUT_NONEMPTY_STATUS
            representative = min(accepted_set)
            offsets = tuple(sorted({_compose(_inverse(representative), p) for p in accepted_set}))
            generated = _enumerate_group(
                offsets or (_identity(semantic["v"]),),
                degree=semantic["v"],
                cap=cap,
                name="parent_filtered_offsets",
            )
            if generated != offsets:
                raise ValueError("parent-valid child candidates are not a single exact right coset")
            parent_stabilizer_elements = offsets
            reconstructed = tuple(sorted({_compose(representative, h) for h in parent_stabilizer_elements}))
            if reconstructed != accepted_set:
                raise ValueError("parent-filtered right-coset reconstruction drift")
        work_bound = (
            semantic["semantic_work_bound"]
            + len(execution["ambient"]) * semantic["v"]
            + candidate_count * semantic["n"] * semantic["k"]
            + len(accepted_set) * semantic["v"]
        )
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "reduction_identity": semantic["reduction_identity"],
            "semantic_binding_identity": semantic["binding_identity"],
            "child_instance_identity": execution["child_instance_identity"],
            "child_result_identity": execution["child_result_identity"],
            "action_degree": semantic["v"],
            "candidate_count": candidate_count,
            "accepted_count": len(accepted_set),
            "representative": representative,
            "parent_stabilizer_elements": parent_stabilizer_elements,
            "work_bound": work_bound,
        }
        result_identity = _sha256(payload)
    except (TypeError, ValueError, OverflowError, KeyError) as exc:
        return _fail(str(exc))

    return ParentFilteredGroundResult(
        SCHEMA_VERSION,
        status,
        True,
        True,
        True,
        semantic["reduction_identity"],
        semantic["binding_identity"],
        execution["child_instance_identity"],
        execution["child_result_identity"],
        semantic["v"],
        candidate_count,
        len(accepted_set),
        representative,
        parent_stabilizer_elements,
        work_bound,
        result_identity,
        (
            "bounded exact child transporter set replayed and every candidate filtered against the complete parent Johnson string; "
            "result is an exact empty set or exact right coset on the Johnson ground only"
        ),
    )


__all__ = [
    "ParentFilteredGroundResult",
    "certify_parent_filtered_child_result",
]
