"""Validation for the public capability-family matrix used to source sealed banks.

The matrix is capability coverage, not final task content. It prevents a sealed
bank registry from silently reducing evaluation to one convenient/trivial family
per domain after the candidate is known.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from eval_core import REQUIRED_DOMAINS, canonical_json

SCHEMA = "agi-family-matrix-v1"
ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
ALLOWED_SHAPES = {"solution", "artifact", "interactive"}
ALLOWED_EVIDENCE = {"json", "workspace"}


def validate_family_matrix(matrix: dict, *, required_domains: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    required_domains = set(required_domains or REQUIRED_DOMAINS)
    if matrix.get("schema") != SCHEMA:
        return [f"schema must be {SCHEMA}"]
    if matrix.get("status") not in {"draft", "frozen"}:
        errors.append("status must be draft or frozen")
    policy = matrix.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be a mapping")
        policy = {}
    minimum = policy.get("minimum_families_per_required_domain")
    if not isinstance(minimum, int) or minimum < 3:
        errors.append("minimum_families_per_required_domain must be integer >= 3")
        minimum = 3
    custodies = policy.get("minimum_independent_custodies_per_family")
    if not isinstance(custodies, int) or custodies < 2:
        errors.append("minimum_independent_custodies_per_family must be integer >= 2")
    if policy.get("family_removal_after_freeze") != "forbidden":
        errors.append("family_removal_after_freeze must be forbidden")
    if policy.get("failed_family_can_be_averaged_away") is not False:
        errors.append("failed_family_can_be_averaged_away must be false")

    domains = matrix.get("required_domains")
    if not isinstance(domains, dict):
        return errors + ["required_domains must be a mapping"]
    missing = sorted(required_domains - set(domains))
    extra = sorted(set(domains) - required_domains)
    if missing:
        errors.append(f"required domains missing from family matrix: {missing}")
    if extra:
        errors.append(f"unexpected required domains in family matrix: {extra}")

    seen: set[str] = set()
    for domain in sorted(required_domains):
        families = domains.get(domain)
        if not isinstance(families, list):
            errors.append(f"{domain}: family list required")
            continue
        if len(families) < minimum:
            errors.append(f"{domain}: {len(families)} families < required {minimum}")
        shapes: set[str] = set()
        for index, row in enumerate(families):
            prefix = f"{domain}[{index}]"
            if not isinstance(row, dict):
                errors.append(f"{prefix}: family must be mapping")
                continue
            fid = row.get("family_id")
            if not isinstance(fid, str) or not ID_RE.fullmatch(fid):
                errors.append(f"{prefix}: invalid family_id")
            elif fid in seen:
                errors.append(f"duplicate family_id {fid}")
            else:
                seen.add(fid)
            shape = row.get("task_shape")
            if shape not in ALLOWED_SHAPES:
                errors.append(f"{prefix}: task_shape must be one of {sorted(ALLOWED_SHAPES)}")
            else:
                shapes.add(str(shape))
            evidence = row.get("success_evidence")
            if evidence not in ALLOWED_EVIDENCE:
                errors.append(f"{prefix}: success_evidence must be one of {sorted(ALLOWED_EVIDENCE)}")
            tags = row.get("capability_tags")
            if not isinstance(tags, list) or len(tags) < 2 or not all(isinstance(x, str) and ID_RE.fullmatch(x) for x in tags):
                errors.append(f"{prefix}: capability_tags needs >=2 identifiers")
            description = row.get("description")
            if not isinstance(description, str) or len(description.strip()) < 40:
                errors.append(f"{prefix}: substantive description required")
        if domain in {"language_knowledge", "software_engineering", "data_analysis", "planning_decision"} and "artifact" not in shapes:
            errors.append(f"{domain}: at least one artifact family required")
        if domain in {"planning_decision", "novel_task_induction"} and "interactive" not in shapes:
            errors.append(f"{domain}: at least one interactive family required")

    optional = matrix.get("optional_domains") or {}
    if not isinstance(optional, dict):
        errors.append("optional_domains must be a mapping")
    elif "multimodal_interpretation" in optional:
        mm = optional["multimodal_interpretation"]
        if not isinstance(mm, dict) or mm.get("activation_rule") != "required_if_X1_exposes_image_audio_or_video_inputs":
            errors.append("multimodal_interpretation activation rule must be tied to X1 non-text inputs")
        elif not isinstance(mm.get("families"), list) or len(mm["families"]) < 3:
            errors.append("multimodal_interpretation requires at least three families when activated")
    return errors


def required_family_map(matrix: dict) -> dict[str, list[str]]:
    errors = validate_family_matrix(matrix)
    if errors:
        raise ValueError("invalid family matrix: " + "; ".join(errors))
    return {
        domain: [str(row["family_id"]) for row in matrix["required_domains"][domain]]
        for domain in sorted(REQUIRED_DOMAINS)
    }


def matrix_commitment(matrix: dict) -> str:
    return hashlib.sha256(canonical_json(matrix).encode()).hexdigest()


def activated_family_map(matrix: dict, *, x1_modalities: set[str] | None = None) -> dict[str, list[str]]:
    result = required_family_map(matrix)
    modalities = set(x1_modalities or {"text"})
    if modalities - {"text"}:
        mm = (matrix.get("optional_domains") or {}).get("multimodal_interpretation") or {}
        families = mm.get("families") or []
        if len(families) < 3:
            raise ValueError("X1 exposes non-text inputs but multimodal family matrix is incomplete")
        result["multimodal_interpretation"] = [str(row["family_id"]) for row in families]
    return result
