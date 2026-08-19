"""Stage-check and structurally qualify sealed generator-bank containers.

Raw qualification tasks are intentionally not written to disk or returned in the
qualification report. Only hashes and structural pass/fail are recorded. This is
a mechanical admission check; it does not establish novelty, task quality,
independence, human calibration, or AGI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from eval_core import REQUIRED_DOMAINS, canonical_json, validate_taskpacks
from freeze_sealed_banks import freeze
from sealed_bank import SealedBankProvider, validate_registry

REPORT_SCHEMA = "agi-sealed-bank-qualification-v1"
QUALIFICATION_PREFIX = "__qualification__:"


def _staged_image_id(image: str) -> str:
    proc = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"staged image inspect failed for {image}")
    image_id = proc.stdout.strip().lower()
    if not image_id.startswith("sha256:"):
        raise RuntimeError(f"unexpected staged image ID for {image}")
    return image_id


def verify_lock(registry: dict, manifest: dict, lock: dict) -> list[str]:
    errors: list[str] = []
    try:
        expected = freeze(registry, manifest)
    except Exception as e:
        return [f"cannot recompute bank lock: {type(e).__name__}: {e}"]
    if canonical_json(expected) != canonical_json(lock):
        errors.append("sealed-bank lock does not match registry/manifest")
    return errors


def _qualification_rows(bank: dict, family: str, generated: dict) -> tuple[dict, dict]:
    tid = f"qualification-{bank['bank_id']}-{family}"
    pub = dict(generated["public"])
    priv = dict(generated["private"])
    pub.pop("task_id", None)
    priv.pop("task_id", None)
    pub.update({"task_id": tid, "domain": bank["domain"], "family": family})
    priv.update({"task_id": tid, "human_reference_lower_bound": 0.0})
    return pub, priv


def qualify_bank(bank: dict, *, manifest: dict, nonce: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    image = str(bank["provider"]["image"])
    declared_digest = str(bank["provider"]["digest"]).lower()
    staged = _staged_image_id(image)
    if staged != declared_digest:
        raise RuntimeError(f"bank {bank['bank_id']} staged image digest mismatch")
    provider = SealedBankProvider.from_bank(bank)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for family in sorted(str(x) for x in bank["families"]):
        try:
            generated = provider.generate(
                domain=str(bank["domain"]),
                family=family,
                seed=f"{QUALIFICATION_PREFIX}{bank['bank_id']}:{family}",
                nonce=nonce,
            )
            pub, priv = _qualification_rows(bank, family, generated)
            task_errors = validate_taskpacks([pub], [priv], manifest, final=False)
            if task_errors:
                raise RuntimeError("qualification task invalid: " + "; ".join(task_errors))
            results.append(
                {
                    "bank_id": bank["bank_id"],
                    "domain": bank["domain"],
                    "family": family,
                    "provider_digest": declared_digest,
                    "public_sha256": hashlib.sha256(canonical_json(generated["public"]).encode()).hexdigest(),
                    "private_sha256": hashlib.sha256(canonical_json(generated["private"]).encode()).hexdigest(),
                    "structural_validation": "passed",
                }
            )
        except Exception as e:
            failures.append(
                {
                    "bank_id": bank.get("bank_id"),
                    "domain": bank.get("domain"),
                    "family": family,
                    "error": f"{type(e).__name__}: {e}",
                }
            )
    return results, failures


def qualify(registry: dict, manifest: dict, lock: dict, *, nonce: str) -> dict[str, Any]:
    errors = validate_registry(registry, required_domains=set(REQUIRED_DOMAINS))
    errors += verify_lock(registry, manifest, lock)
    if errors:
        raise ValueError("prequalification invalid: " + "; ".join(errors))
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    expected_assignments = sum(len(bank["families"]) for bank in registry["banks"])
    for bank in sorted(registry["banks"], key=lambda row: str(row["bank_id"])):
        try:
            passed, failed = qualify_bank(bank, manifest=manifest, nonce=nonce)
            results.extend(passed)
            failures.extend(failed)
        except Exception as e:
            failures.append(
                {
                    "bank_id": bank.get("bank_id"),
                    "domain": bank.get("domain"),
                    "family": None,
                    "error": f"{type(e).__name__}: {e}",
                }
            )
    report = {
        "schema": REPORT_SCHEMA,
        "registry_sha256": lock["registry_sha256"],
        "bank_lock_payload_sha256": lock["payload_sha256"],
        "qualification_nonce_sha256": hashlib.sha256(nonce.encode()).hexdigest(),
        "expected_family_assignments": expected_assignments,
        "qualified": results,
        "failures": failures,
        "passed": not failures and len(results) == expected_assignments,
    }
    payload = dict(report)
    report["payload_sha256"] = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--registry", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--lock", required=True)
    p.add_argument("--nonce", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    try:
        registry = yaml.safe_load(Path(args.registry).read_text(encoding="utf-8"))
        manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
        lock = json.loads(Path(args.lock).read_text(encoding="utf-8"))
        if not all(isinstance(x, dict) for x in (registry, manifest, lock)):
            raise ValueError("registry, manifest and lock must be mappings")
        if len(args.nonce) < 16:
            raise ValueError("qualification nonce must be at least 16 characters")
        report = qualify(registry, manifest, lock, nonce=args.nonce)
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as e:
        print(json.dumps({"qualified": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps({"qualified": report["passed"], "assignments": len(report["qualified"]), "failures": len(report["failures"]), "payload_sha256": report["payload_sha256"]}, sort_keys=True))
    return 0 if report["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
