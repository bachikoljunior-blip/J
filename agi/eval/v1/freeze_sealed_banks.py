"""Validate and cryptographically freeze a sealed-generator-bank registry."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

from eval_core import REQUIRED_DOMAINS, canonical_json, load_yaml
from sealed_bank import REGISTRY_SCHEMA, coverage_summary, registry_commitment, validate_registry

LOCK_SCHEMA = "agi-sealed-bank-lock-v1"


def freeze(registry: dict, manifest: dict) -> dict:
    manifest_domains = set(manifest.get("domains") or [])
    required = set(REQUIRED_DOMAINS)
    if not required.issubset(manifest_domains):
        missing = sorted(required - manifest_domains)
        raise ValueError(f"manifest missing required domains: {missing}")
    errors = validate_registry(registry, required_domains=required)
    if errors:
        raise ValueError("sealed-bank registry invalid: " + "; ".join(errors))
    identities = []
    for bank in sorted(registry["banks"], key=lambda row: str(row["bank_id"])):
        identities.append(
            {
                "bank_id": bank["bank_id"],
                "domain": bank["domain"],
                "families": sorted(bank["families"]),
                "custody_group": bank["custody_group"],
                "implementation_lineage": bank["implementation_lineage"],
                "provider_digest": bank["provider"]["digest"].lower(),
                "sealed_content_commitment": str(bank["sealed_content_commitment"]).removeprefix("sha256:").lower(),
                "seed_schedule_commitment": str(bank["seed_schedule_commitment"]).removeprefix("sha256:").lower(),
            }
        )
    payload = {
        "schema": LOCK_SCHEMA,
        "registry_schema": REGISTRY_SCHEMA,
        "registry_sha256": registry_commitment(registry),
        "manifest_sha256": hashlib.sha256(canonical_json(manifest).encode()).hexdigest(),
        "required_domains": sorted(required),
        "minimum_independent_custodies_per_family": registry["minimum_independent_custodies_per_family"],
        "coverage": coverage_summary(registry, required_domains=required),
        "bank_identities": identities,
    }
    payload["payload_sha256"] = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--registry", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    try:
        registry = yaml.safe_load(Path(args.registry).read_text(encoding="utf-8"))
        if not isinstance(registry, dict):
            raise ValueError("registry top level must be a mapping")
        manifest = load_yaml(args.manifest)
        lock = freeze(registry, manifest)
        Path(args.out).write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as e:
        print(json.dumps({"frozen": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps({"frozen": True, "banks": len(lock["bank_identities"]), "payload_sha256": lock["payload_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
