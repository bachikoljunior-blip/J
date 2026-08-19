"""Verify structural and cryptographic integrity of an AGI eval evidence bundle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from eval_core import canonical_json, load_jsonl, sha256_bytes, sha256_file, summarize_records, verify_hash_chain


def _verify_arena_records(artifact: dict, records: list[dict]) -> list[str]:
    errors: list[str] = []
    if (artifact.get("run") or {}).get("runner") != "arena-v1":
        return errors
    try:
        from autonomy import derive_autonomy_metrics, verify_telemetry
        from run_arena_harness import aggregate_autonomy
    except Exception as e:
        return [f"arena verifier import failed: {type(e).__name__}: {e}"]
    for i, rec in enumerate(records):
        events = rec.get("autonomy_telemetry")
        tip = rec.get("autonomy_telemetry_tip")
        if not isinstance(events, list):
            errors.append(f"record[{i}] missing autonomy telemetry")
            continue
        for error in verify_telemetry(events, tip):
            errors.append(f"record[{i}] telemetry: {error}")
        try:
            derived = derive_autonomy_metrics(events)
            if canonical_json(derived) != canonical_json(rec.get("autonomy_metrics")):
                errors.append(f"record[{i}] autonomy metrics do not match telemetry")
        except Exception as e:
            errors.append(f"record[{i}] autonomy metric derivation failed: {type(e).__name__}: {e}")
    try:
        expected = aggregate_autonomy(records)
        stored = (artifact.get("summary") or {}).get("autonomy_metrics")
        if canonical_json(expected) != canonical_json(stored):
            errors.append("aggregate autonomy metrics do not match records")
    except Exception as e:
        errors.append(f"aggregate autonomy verification failed: {type(e).__name__}: {e}")
    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--public", required=True)
    p.add_argument("--private", required=True)
    p.add_argument("--lock", required=True)
    args = p.parse_args()
    errors = []
    artifact = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    lock = json.loads(Path(args.lock).read_text(encoding="utf-8"))
    run = artifact.get("run") or {}
    expected_hashes = {
        "manifest_sha256": sha256_file(args.manifest),
        "public_pack_sha256": sha256_file(args.public),
        "private_pack_sha256": sha256_file(args.private),
        "lock_sha256": sha256_file(args.lock),
    }
    for k, v in expected_hashes.items():
        if run.get(k) != v:
            errors.append(f"evidence run hash mismatch: {k}")
    payload = {k: v for k, v in lock.items() if k != "payload_sha256"}
    if lock.get("payload_sha256") != sha256_bytes(canonical_json(payload).encode()):
        errors.append("lock payload hash invalid")
    records = artifact.get("records")
    if not isinstance(records, list):
        errors.append("records missing")
        records = []
    errors += verify_hash_chain(records, artifact.get("record_hash_chain_tip"))
    errors += _verify_arena_records(artifact, records)
    try:
        manifest = yaml.safe_load(Path(args.manifest).read_text())
        private = load_jsonl(args.private)
        recomputed = summarize_records(records, private, manifest)
        stored = dict(artifact.get("summary") or {})
        for k in ["total_tasks", "passed_tasks", "failed_tasks", "autonomy_metrics"]:
            stored.pop(k, None)
        if canonical_json(stored) != canonical_json(recomputed):
            errors.append("summary does not match records")
    except Exception as e:
        errors.append(f"summary recomputation failed: {type(e).__name__}: {e}")
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
