"""Create a cryptographic lock for a candidate + manifest + sealed task packs."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from eval_core import (
    SCHEMA,
    canonical_json,
    load_jsonl,
    load_yaml,
    sha256_bytes,
    sha256_file,
    validate_manifest,
    validate_taskpacks,
)


def build_lock(args) -> dict:
    final = args.mode == "final"
    manifest = load_yaml(args.manifest)
    public = load_jsonl(args.public)
    private = load_jsonl(args.private)
    errors = validate_manifest(manifest, final=final)
    errors += validate_taskpacks(public, private, manifest, final=final)
    if errors:
        raise ValueError("cannot freeze invalid evaluation:\n- " + "\n- ".join(errors))
    if not args.candidate_id.strip() or not args.candidate_digest.strip():
        raise ValueError("candidate-id and candidate-digest are required")
    if final and not args.candidate_digest.startswith("sha256:"):
        raise ValueError("final candidate-digest must be a sha256:... immutable digest")
    if final and not args.generator_provenance:
        raise ValueError("final freeze requires generator provenance")

    payload = {
        "schema": "agi-eval-lock-v1",
        "eval_schema": SCHEMA,
        "mode": args.mode,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_id": args.candidate_id,
        "candidate_digest": args.candidate_digest,
        "manifest_sha256": sha256_file(args.manifest),
        "public_pack_sha256": sha256_file(args.public),
        "private_pack_sha256": sha256_file(args.private),
        "generator_provenance_sha256": sha256_file(args.generator_provenance) if args.generator_provenance else None,
        "task_count": len(public),
        "manifest_status": manifest.get("status"),
    }
    payload["payload_sha256"] = sha256_bytes(canonical_json(payload).encode("utf-8"))
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--public", required=True)
    p.add_argument("--private", required=True)
    p.add_argument("--candidate-id", required=True)
    p.add_argument("--candidate-digest", required=True)
    p.add_argument("--generator-provenance")
    p.add_argument("--mode", choices=["development", "final"], default="development")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    try:
        lock = build_lock(args)
    except Exception as e:
        print(f"FREEZE FAILED: {e}")
        return 2
    Path(args.out).write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"locked": True, "mode": args.mode, "payload_sha256": lock["payload_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
