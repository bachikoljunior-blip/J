from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ALLOWED_TOOL_CATEGORIES = {"deterministic", "retrieval", "environment", "sensor", "task_api"}
PROHIBITED_COGNITIVE_CATEGORIES = {"general_model", "human_operator", "project_solver"}


@dataclass(frozen=True)
class ManifestValidation:
    valid: bool
    reasons: tuple[str, ...]


def validate_candidate_manifest(manifest: Mapping[str, Any]) -> ManifestValidation:
    reasons: list[str] = []
    for key in ("candidate_id", "artifact_sha256", "runtime_sha256", "model_boundary", "tools"):
        if key not in manifest:
            reasons.append(f"missing {key}")

    if not _sha256ish(manifest.get("artifact_sha256")):
        reasons.append("artifact_sha256 must be a lowercase 64-hex digest")
    if not _sha256ish(manifest.get("runtime_sha256")):
        reasons.append("runtime_sha256 must be a lowercase 64-hex digest")

    boundary = manifest.get("model_boundary")
    if not isinstance(boundary, Mapping):
        reasons.append("model_boundary must be an object")
    else:
        if boundary.get("includes_project_solver") is not False:
            reasons.append("project solver must be explicitly excluded")
        if boundary.get("allows_undisclosed_remote_cognition") is not False:
            reasons.append("undisclosed remote cognition must be explicitly forbidden")
        components = boundary.get("components")
        if not isinstance(components, Sequence) or isinstance(components, (str, bytes)) or not components:
            reasons.append("model_boundary.components must list the frozen cognitive components")

    tools = manifest.get("tools")
    if not isinstance(tools, Sequence) or isinstance(tools, (str, bytes)):
        reasons.append("tools must be a list")
    else:
        seen: set[str] = set()
        for idx, tool in enumerate(tools):
            if not isinstance(tool, Mapping):
                reasons.append(f"tool[{idx}] must be an object")
                continue
            name = str(tool.get("name", ""))
            category = str(tool.get("category", ""))
            if not name:
                reasons.append(f"tool[{idx}] missing name")
            elif name in seen:
                reasons.append(f"duplicate tool name: {name}")
            seen.add(name)
            if category in PROHIBITED_COGNITIVE_CATEGORIES:
                reasons.append(f"tool {name or idx}: prohibited cognitive category {category}")
            elif category not in ALLOWED_TOOL_CATEGORIES:
                reasons.append(f"tool {name or idx}: undeclared/unknown category {category}")
            if tool.get("logs_arguments_digest") is not True or tool.get("logs_result_digest") is not True:
                reasons.append(f"tool {name or idx}: argument/result digest logging required")

    endpoints = manifest.get("network_endpoints", [])
    if not isinstance(endpoints, Sequence) or isinstance(endpoints, (str, bytes)):
        reasons.append("network_endpoints must be a list")
    else:
        for idx, endpoint in enumerate(endpoints):
            if not isinstance(endpoint, Mapping):
                reasons.append(f"network_endpoints[{idx}] must be an object")
                continue
            if endpoint.get("declared") is not True:
                reasons.append(f"network_endpoints[{idx}] is not explicitly declared")
            if endpoint.get("provides_general_cognition") is True:
                reasons.append(f"network_endpoints[{idx}] provides prohibited general cognition")

    return ManifestValidation(not reasons, tuple(reasons))


def _sha256ish(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(ch in "0123456789abcdef" for ch in value)
