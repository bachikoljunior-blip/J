"""Freeze the public family matrix together with the sealed-bank registry.

This gate prevents a final bank registry from silently shrinking the preregistered
capability-family surface. It currently supports the text/tool/file candidate
surface. If X1 exposes non-text modalities, this v1 gate fails closed until the
optional multimodal domain is promoted into the final manifest and bank registry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from eval_core import REQUIRED_DOMAINS, canonical_json, load_yaml
from family_matrix import matrix_commitment, required_family_map, validate_family_matrix
from freeze_sealed_banks import freeze as freeze_banks
from sealed_bank import validate_registry

SCHEMA = "agi-foundry-input-lock-v1"


def freeze_foundry_inputs(
    family_matrix: dict,
    registry: dict,
    manifest: dict,
    *,
    x1_modalities: set[str] | None = None,
) -> dict[str, Any]:
    modalities = set(x1_modalities or {"text"})
    if modalities - {"text"}:
        raise ValueError(
            "foundry-input lock v1 supports only text/tool/file candidate inputs; "
            "non-text X1 modalities require promoting multimodal_interpretation into the final manifest/registry"
        )
    matrix_errors = validate_family_matrix(family_matrix, required_domains=set(REQUIRED_DOMAINS))
    if matrix_errors:
        raise ValueError("family matrix invalid: " + "; ".join(matrix_errors))
    expected = required_family_map(family_matrix)
    actual = registry.get("required_families")
    if canonical_json(actual) != canonical_json(expected):
        raise ValueError("sealed-bank required_families must exactly match the preregistered family matrix")
    matrix_min = int(family_matrix["policy"]["minimum_independent_custodies_per_family"])
    registry_min = registry.get("minimum_independent_custodies_per_family")
    if not isinstance(registry_min, int) or registry_min < matrix_min:
        raise ValueError("sealed-bank custody minimum is below the family-matrix minimum")
    registry_errors = validate_registry(registry, required_domains=set(REQUIRED_DOMAINS))
    if registry_errors:
        raise ValueError("sealed-bank registry invalid: " + "; ".join(registry_errors))
    bank_lock = freeze_banks(registry, manifest)
    payload = {
        "schema": SCHEMA,
        "x1_modalities": sorted(modalities),
        "family_matrix_sha256": matrix_commitment(family_matrix),
        "family_matrix_status": family_matrix["status"],
        "required_families": expected,
        "sealed_bank_lock": bank_lock,
    }
    payload["payload_sha256"] = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--family-matrix", required=True)
    p.add_argument("--registry", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--x1-modalities", nargs="+", default=["text"])
    p.add_argument("--out", required=True)
    args = p.parse_args()
    try:
        matrix = yaml.safe_load(Path(args.family_matrix).read_text(encoding="utf-8"))
        registry = yaml.safe_load(Path(args.registry).read_text(encoding="utf-8"))
        manifest = load_yaml(args.manifest)
        if not isinstance(matrix, dict) or not isinstance(registry, dict):
            raise ValueError("family matrix and registry must be mappings")
        lock = freeze_foundry_inputs(matrix, registry, manifest, x1_modalities=set(args.x1_modalities))
        Path(args.out).write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as e:
        print(json.dumps({"frozen": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps({"frozen": True, "payload_sha256": lock["payload_sha256"], "families": sum(len(v) for v in lock["required_families"].values())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
