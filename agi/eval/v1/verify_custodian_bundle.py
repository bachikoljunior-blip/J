"""Verify signed custodian acceptances and documentary family coverage as one gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from custodian_acceptance import load_family_map, validate_acceptance, validate_coverage, verify_ssh_signature
from eval_core import canonical_json

SCHEMA = "agi-custodian-bundle-v1"


def verify_bundle(bundle: dict, *, family_matrix_path: str | Path, allowed_signers_path: str | Path, base_dir: str | Path) -> dict:
    if bundle.get("schema") != SCHEMA:
        raise ValueError(f"bundle schema must be {SCHEMA}")
    minimum = bundle.get("minimum_independent_custodians_per_family", 2)
    if not isinstance(minimum, int) or minimum < 2:
        raise ValueError("minimum_independent_custodians_per_family must be integer >=2")
    entries = bundle.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("bundle entries must be non-empty")
    fmap = load_family_map(family_matrix_path)
    root = Path(base_dir).resolve()
    records: list[dict] = []
    verified: list[dict] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"entries[{index}] must be a mapping")
        record_rel, sig_rel = entry.get("record"), entry.get("signature")
        if not isinstance(record_rel, str) or not isinstance(sig_rel, str):
            raise ValueError(f"entries[{index}] record/signature paths required")
        record_path, sig_path = (root / record_rel).resolve(), (root / sig_rel).resolve()
        if root not in record_path.parents or root not in sig_path.parents:
            raise ValueError(f"entries[{index}] path escapes bundle directory")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError(f"entries[{index}] record must be a JSON object")
        errors = validate_acceptance(record, fmap)
        if errors:
            raise ValueError(f"entries[{index}] invalid: " + "; ".join(errors))
        ok, detail = verify_ssh_signature(record, signature_path=sig_path, allowed_signers_path=allowed_signers_path)
        if not ok:
            raise ValueError(f"entries[{index}] invalid SSH signature: {detail}")
        records.append(record)
        verified.append(
            {
                "custodian_id": record["custodian_id"],
                "signing_principal": record["signing_principal"],
                "record_sha256": hashlib.sha256((canonical_json(record) + "\n").encode()).hexdigest(),
                "signature_sha256": hashlib.sha256(sig_path.read_bytes()).hexdigest(),
                "assignments": len(record["assignments"]),
            }
        )
    coverage_errors = validate_coverage(records, fmap, minimum=minimum)
    if coverage_errors:
        raise ValueError("custodian coverage invalid: " + "; ".join(coverage_errors))
    report = {
        "schema": "agi-custodian-bundle-verification-v1",
        "minimum_independent_custodians_per_family": minimum,
        "verified_acceptances": verified,
        "coverage": "documentary_complete",
        "independence_truth_status": "requires_external_identity_and_conflict_audit",
    }
    report["payload_sha256"] = hashlib.sha256(canonical_json(report).encode()).hexdigest()
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", required=True)
    p.add_argument("--family-matrix", required=True)
    p.add_argument("--allowed-signers", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    try:
        bundle_path = Path(args.bundle)
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        if not isinstance(bundle, dict):
            raise ValueError("bundle must be a JSON object")
        report = verify_bundle(
            bundle,
            family_matrix_path=args.family_matrix,
            allowed_signers_path=args.allowed_signers,
            base_dir=bundle_path.parent,
        )
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as e:
        print(json.dumps({"verified": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps({"verified": True, "acceptances": len(report["verified_acceptances"]), "payload_sha256": report["payload_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
